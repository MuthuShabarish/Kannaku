import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from fastapi import HTTPException, status

from app.models.business import Warehouse, Branch
from app.models.supplier import Supplier, SupplierLedgerEntry
from app.models.inventory import Product, InventoryBalance, StockMovement
from app.models.purchase import Purchase, PurchaseItem
from app.models.sales import Payment
from app.models.user import User
from app.schemas.purchase import PurchaseCreate
from app.services.inventory_service import get_default_warehouse

FOUR_PLACES = Decimal("0.0001")


def generate_purchase_invoice_number(db: Session, business_id: uuid.UUID) -> str:
    """Generates a sequential human-readable purchase invoice identifier: PUR-YYYYMMDD-XXXX."""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"PUR-{today_str}-"

    count_today = (
        db.query(func.count(Purchase.id))
        .filter(Purchase.business_id == business_id, Purchase.invoice_number.like(f"{prefix}%"))
        .scalar()
    ) or 0

    seq = count_today + 1
    invoice_number = f"{prefix}{seq:04d}"

    # Handle rare collision
    collision = (
        db.query(Purchase)
        .filter(Purchase.business_id == business_id, Purchase.invoice_number == invoice_number)
        .first()
    )
    while collision:
        seq += 1
        invoice_number = f"{prefix}{seq:04d}"
        collision = (
            db.query(Purchase)
            .filter(Purchase.business_id == business_id, Purchase.invoice_number == invoice_number)
            .first()
        )

    return invoice_number


def _format_purchase_response(purchase: Purchase) -> dict:
    """Helper to convert Purchase ORM object into a dictionary compatible with PurchaseResponse schema."""
    items = []
    for it in purchase.items:
        items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": it.product_name,
            "sku": it.sku,
            "unit": it.unit,
            "quantity": it.quantity,
            "unit_cost": it.unit_cost,
            "discount_amount": it.discount_amount,
            "total_cost": it.total_cost,
            "effective_unit_cost": it.effective_unit_cost,
        })

    payments = []
    for p in purchase.payments:
        payments.append({
            "id": p.id,
            "payment_mode": p.payment_mode,
            "amount": p.amount,
            "notes": p.notes,
            "created_at": p.created_at,
        })

    return {
        "id": purchase.id,
        "business_id": purchase.business_id,
        "invoice_number": purchase.invoice_number,
        "supplier_invoice_ref": purchase.supplier_invoice_ref,
        "supplier_id": purchase.supplier_id,
        "supplier_name": purchase.supplier.name if purchase.supplier else None,
        "supplier_phone": purchase.supplier.phone if purchase.supplier else None,
        "status": purchase.status,
        "subtotal_amount": purchase.subtotal_amount,
        "discount_amount": purchase.discount_amount,
        "tax_amount": purchase.tax_amount,
        "total_amount": purchase.total_amount,
        "paid_amount": purchase.paid_amount,
        "credit_amount": purchase.credit_amount,
        "payment_method": purchase.payment_method,
        "payment_status": purchase.payment_status,
        "purchase_date": purchase.purchase_date,
        "notes": purchase.notes,
        "created_by_user_id": purchase.created_by_user_id,
        "created_by_user_name": purchase.created_by_user.full_name if purchase.created_by_user else None,
        "created_at": purchase.created_at,
        "items": items,
        "payments": payments,
    }


def create_purchase(
    db: Session,
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: PurchaseCreate
) -> dict:
    """
    Executes an atomic purchase receiving transaction in PostgreSQL:
    1. Idempotency control: Returns existing purchase if idempotency_key was already processed.
    2. Sorts product IDs deterministically to lock InventoryBalances with with_for_update() (deadlock prevention).
    3. Validates products exist, are active, and quantities > 0.
    4. Calculates line totals, landed costs, and allocates overall invoice discounts proportionally.
    5. Calculates new Moving-Average Cost (MAC) and updates InventoryBalance with incoming stock.
    6. Records immutable StockMovement ledger entries (movement_type='purchase').
    7. Validates payment methods (Cash, UPI, Card, Bank Transfer, Credit, Split).
    8. Updates supplier AP balance and writes SupplierLedgerEntry if credit was extended.
    9. Commits the transaction atomically.
    """
    # 1. Idempotency check
    if req.idempotency_key:
        clean_key = req.idempotency_key.strip()
        existing_purchase = (
            db.query(Purchase)
            .filter(Purchase.business_id == business_id, Purchase.idempotency_key == clean_key)
            .first()
        )
        if existing_purchase:
            return _format_purchase_response(existing_purchase)

    # 2. Resolve default branch and warehouse
    warehouse = get_default_warehouse(db, business_id)
    branch_id = warehouse.branch_id

    # 3. Collect product IDs & calculate aggregated quantities per product
    product_qty_map: Dict[uuid.UUID, Decimal] = {}
    for item in req.items:
        qty = item.quantity.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if qty <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_QUANTITY", "message": "Quantity must be greater than zero."}
            )
        cost = item.unit_cost.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if cost < Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_UNIT_COST", "message": "Unit cost cannot be negative."}
            )
        product_qty_map[item.product_id] = product_qty_map.get(item.product_id, Decimal("0.0000")) + qty

    distinct_product_ids = sorted(list(product_qty_map.keys()))

    # 4. Pessimistic row locking on InventoryBalance in deterministic order
    balances = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.warehouse_id == warehouse.id,
            InventoryBalance.product_id.in_(distinct_product_ids),
            InventoryBalance.business_id == business_id
        )
        .with_for_update()
        .all()
    )
    balance_map = {b.product_id: b for b in balances}

    # Fetch product definitions
    products = (
        db.query(Product)
        .filter(Product.id.in_(distinct_product_ids), Product.business_id == business_id)
        .all()
    )
    prod_map = {p.id: p for p in products}

    # Validate all products exist and are active
    for p_id in distinct_product_ids:
        if p_id not in prod_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PRODUCT_NOT_FOUND", "message": f"Product with ID {p_id} not found."}
            )
        prod = prod_map[p_id]
        if not prod.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "PRODUCT_INACTIVE", "message": f"Product '{prod.name}' is inactive and cannot be purchased."}
            )

        # Ensure InventoryBalance exists in map (or create)
        if p_id not in balance_map:
            new_bal = InventoryBalance(
                business_id=business_id,
                warehouse_id=warehouse.id,
                product_id=p_id,
                current_stock=Decimal("0.0000"),
                reserved_stock=Decimal("0.0000"),
                average_cost=prod.purchase_cost
            )
            db.add(new_bal)
            db.flush()
            balance_map[p_id] = new_bal

    # 5. Calculate preliminary line totals
    prelim_items = []
    subtotal = Decimal("0.0000")

    for item in req.items:
        prod = prod_map[item.product_id]
        qty = item.quantity.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        unit_cost = item.unit_cost.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        line_sub = (qty * unit_cost).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        line_disc = item.discount_amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        if line_disc > line_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_LINE_DISCOUNT",
                    "message": f"Line discount of {line_disc} exceeds item total of {line_sub} for '{prod.name}'."
                }
            )

        line_tot = line_sub - line_disc
        subtotal += line_tot

        prelim_items.append({
            "product": prod,
            "quantity": qty,
            "unit_cost": unit_cost,
            "discount_amount": line_disc,
            "line_net": line_tot
        })

    # 6. Overall Bill Discount & Landed Cost Allocation
    overall_discount = req.discount_amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    if overall_discount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_OVERALL_DISCOUNT", "message": "Overall discount cannot exceed purchase subtotal."}
        )

    total_amount = (subtotal - overall_discount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    # Landed unit cost allocation: distribute overall discount proportionally
    line_records: List[PurchaseItem] = []
    product_received_totals: Dict[uuid.UUID, Dict[str, Decimal]] = {}

    for it in prelim_items:
        prod = it["product"]
        qty = it["quantity"]
        unit_cost = it["unit_cost"]
        line_net = it["line_net"]

        if subtotal > Decimal("0.0000"):
            item_allocated_discount = (line_net / subtotal) * overall_discount
        else:
            item_allocated_discount = Decimal("0.0000")

        net_landed_cost = (line_net - item_allocated_discount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        effective_unit_cost = (net_landed_cost / qty).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        # Track per-product received quantities and landed values for MAC calculation
        if prod.id not in product_received_totals:
            product_received_totals[prod.id] = {
                "qty": Decimal("0.0000"),
                "value": Decimal("0.0000")
            }
        product_received_totals[prod.id]["qty"] += qty
        product_received_totals[prod.id]["value"] += net_landed_cost

        purchase_item = PurchaseItem(
            product_id=prod.id,
            product_name=prod.name,
            sku=prod.sku,
            unit=prod.unit,
            quantity=qty,
            unit_cost=unit_cost,
            discount_amount=it["discount_amount"],
            total_cost=line_net,
            effective_unit_cost=effective_unit_cost
        )
        line_records.append(purchase_item)

    # 7. Supplier validation
    supplier = None
    if req.supplier_id:
        supplier = (
            db.query(Supplier)
            .filter(Supplier.id == req.supplier_id, Supplier.business_id == business_id)
            .with_for_update()
            .first()
        )
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SUPPLIER_NOT_FOUND", "message": "Specified supplier does not exist."}
            )
        if not supplier.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUPPLIER_INACTIVE", "message": "Specified supplier is inactive."}
            )

    # 8. Payment calculation and verification
    payment_records: List[Payment] = []
    paid_amount = Decimal("0.0000")
    credit_amount = Decimal("0.0000")

    if req.payment_method in ("cash", "upi", "card", "bank_transfer"):
        if req.paid_amount is None:
            paid_amount = total_amount
        else:
            paid_amount = req.paid_amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        if paid_amount > total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OVERPAID", "message": "Paid amount cannot exceed total purchase amount."}
            )

        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if credit_amount > Decimal("0.0000") and not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SUPPLIER_REQUIRED_FOR_CREDIT",
                    "message": "Partial payment creates a payable balance; please associate a supplier."
                }
            )

        if paid_amount >= total_amount:
            payment_status = "paid"
        elif paid_amount > Decimal("0.0000"):
            payment_status = "partial"
        else:
            payment_status = "unpaid"

        if paid_amount > Decimal("0.0000"):
            payment_records.append(Payment(
                business_id=business_id,
                supplier_id=supplier.id if supplier else None,
                payment_direction="outflow",
                payment_mode=req.payment_method,
                amount=paid_amount,
                notes="Payment for purchase",
                created_by_user_id=user_id
            ))

    elif req.payment_method == "credit":
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUPPLIER_REQUIRED_FOR_CREDIT", "message": "A supplier is required for credit purchases."}
            )

        paid_amount = (req.paid_amount or Decimal("0.0000")).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if paid_amount > total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OVERPAID", "message": "Paid amount cannot exceed total purchase amount."}
            )

        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        payment_status = "unpaid" if paid_amount == Decimal("0.0000") else ("partial" if paid_amount < total_amount else "paid")

        if paid_amount > Decimal("0.0000"):
            payment_records.append(Payment(
                business_id=business_id,
                supplier_id=supplier.id,
                payment_direction="outflow",
                payment_mode="cash",
                amount=paid_amount,
                notes="Initial payment on credit purchase",
                created_by_user_id=user_id
            ))

    elif req.payment_method == "split":
        if not req.split_payments or len(req.split_payments) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SPLIT_PAYMENTS_REQUIRED", "message": "Split payment requires payment items."}
            )

        split_sum = sum(p.amount for p in req.split_payments).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if split_sum > total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OVERPAID", "message": f"Split payments total {split_sum} exceeds purchase amount {total_amount}."}
            )

        paid_amount = split_sum
        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        if credit_amount > Decimal("0.0000") and not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUPPLIER_REQUIRED_FOR_CREDIT", "message": "Supplier required for remaining payable balance."}
            )

        payment_status = "paid" if credit_amount == Decimal("0.0000") else ("partial" if paid_amount > Decimal("0.0000") else "unpaid")

        for sp in req.split_payments:
            sp_amt = sp.amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            if sp_amt > Decimal("0.0000"):
                payment_records.append(Payment(
                    business_id=business_id,
                    supplier_id=supplier.id if supplier else None,
                    payment_direction="outflow",
                    payment_mode=sp.mode,
                    amount=sp_amt,
                    notes=f"Split payment ({sp.mode})",
                    created_by_user_id=user_id
                ))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYMENT_METHOD", "message": f"Unsupported payment method '{req.payment_method}'."}
        )

    # 9. Generate Invoice Number
    invoice_number = generate_purchase_invoice_number(db, business_id)

    try:
        # 10. Create Purchase entity
        purchase = Purchase(
            business_id=business_id,
            branch_id=branch_id,
            warehouse_id=warehouse.id,
            supplier_id=supplier.id if supplier else None,
            invoice_number=invoice_number,
            supplier_invoice_ref=req.supplier_invoice_ref.strip() if req.supplier_invoice_ref else None,
            idempotency_key=req.idempotency_key.strip() if req.idempotency_key else None,
            status="received",
            subtotal_amount=subtotal,
            discount_amount=overall_discount,
            tax_amount=Decimal("0.0000"),
            total_amount=total_amount,
            paid_amount=paid_amount,
            credit_amount=credit_amount,
            payment_method=req.payment_method,
            payment_status=payment_status,
            purchase_date=req.purchase_date or datetime.now(timezone.utc),
            notes=req.notes.strip() if req.notes else None,
            created_by_user_id=user_id
        )
        db.add(purchase)
        db.flush()

        # 11. Add Purchase Items
        for item_rec in line_records:
            item_rec.purchase_id = purchase.id
            db.add(item_rec)

        # 12. Update Inventory Balances with Moving-Average Cost and record StockMovement
        for p_id, rec_totals in product_received_totals.items():
            bal = balance_map[p_id]
            prod = prod_map[p_id]
            received_qty = rec_totals["qty"]
            received_value = rec_totals["value"]

            old_stock = bal.current_stock
            old_cost = bal.average_cost

            # Moving Average Cost calculation:
            if old_stock <= Decimal("0.0000"):
                new_cost = (received_value / received_qty).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            else:
                old_value = old_stock * old_cost
                new_cost = ((old_value + received_value) / (old_stock + received_qty)).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

            new_stock = (old_stock + received_qty).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            bal.current_stock = new_stock
            bal.average_cost = new_cost

            # Also update product's default purchase_cost to latest received landed cost
            effective_incoming_cost = (received_value / received_qty).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            prod.purchase_cost = effective_incoming_cost

            # Stock movement log
            movement = StockMovement(
                business_id=business_id,
                warehouse_id=warehouse.id,
                product_id=p_id,
                movement_type="purchase",
                quantity_delta=received_qty,
                balance_after=new_stock,
                unit_cost=effective_incoming_cost,
                reason=f"Purchase {invoice_number}",
                created_by_user_id=user_id
            )
            db.add(movement)

        # 13. Record Payments
        for pmt in payment_records:
            pmt.purchase_id = purchase.id
            db.add(pmt)

        # 14. If credit amount, update Supplier AP & record Ledger entry
        if credit_amount > Decimal("0.0000") and supplier:
            new_supplier_balance = (supplier.current_balance + credit_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            supplier.current_balance = new_supplier_balance

            ledger_entry = SupplierLedgerEntry(
                business_id=business_id,
                supplier_id=supplier.id,
                entry_type="credit_purchase",
                reference_id=purchase.id,
                amount=credit_amount,
                balance_after=new_supplier_balance,
                notes=f"Credit for purchase {invoice_number}",
                created_by_user_id=user_id
            )
            db.add(ledger_entry)

        # 15. Commit single PostgreSQL transaction
        db.commit()
        db.refresh(purchase)

        return _format_purchase_response(purchase)
    except Exception:
        db.rollback()
        raise


def get_purchase_detail(
    db: Session,
    business_id: uuid.UUID,
    purchase_id: uuid.UUID
) -> dict:
    """Fetches completed purchase details including line items and payment transactions."""
    purchase = (
        db.query(Purchase)
        .filter(Purchase.id == purchase_id, Purchase.business_id == business_id)
        .first()
    )
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PURCHASE_NOT_FOUND", "message": "Purchase transaction not found."}
        )

    return _format_purchase_response(purchase)


def list_purchases(
    db: Session,
    business_id: uuid.UUID,
    search: Optional[str] = None,
    supplier_id: Optional[uuid.UUID] = None,
    payment_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[dict], int]:
    """Lists purchase invoices with pagination and search."""
    query = (
        db.query(Purchase)
        .filter(Purchase.business_id == business_id)
    )

    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)

    if payment_status:
        query = query.filter(Purchase.payment_status == payment_status)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.outerjoin(Supplier, Supplier.id == Purchase.supplier_id).filter(
            or_(
                func.lower(Purchase.invoice_number).ilike(s),
                func.lower(Purchase.supplier_invoice_ref).ilike(s),
                func.lower(Supplier.name).ilike(s),
                Supplier.phone.ilike(s)
            )
        )

    total_count = query.count()
    purchases = query.order_by(Purchase.created_at.desc()).offset(offset).limit(limit).all()

    return [_format_purchase_response(p) for p in purchases], total_count


def get_purchases_overview(db: Session, business_id: uuid.UUID) -> dict:
    """Aggregates purchase metrics (total volume, purchase amount, paid, credit, supplier payables)."""
    purchase_agg = (
        db.query(
            func.count(Purchase.id).label("total_count"),
            func.coalesce(func.sum(Purchase.total_amount), Decimal("0.0000")).label("total_amount"),
            func.coalesce(func.sum(Purchase.paid_amount), Decimal("0.0000")).label("total_paid"),
            func.coalesce(func.sum(Purchase.credit_amount), Decimal("0.0000")).label("total_credit")
        )
        .filter(Purchase.business_id == business_id, Purchase.status == "received")
        .first()
    )

    supplier_agg = (
        db.query(
            func.count(Supplier.id).label("total_suppliers"),
            func.coalesce(func.sum(Supplier.current_balance), Decimal("0.0000")).label("total_payable")
        )
        .filter(Supplier.business_id == business_id, Supplier.is_active == True)
        .first()
    )

    return {
        "total_purchases_count": purchase_agg.total_count if purchase_agg else 0,
        "total_purchases_amount": purchase_agg.total_amount if purchase_agg else Decimal("0.0000"),
        "total_paid_amount": purchase_agg.total_paid if purchase_agg else Decimal("0.0000"),
        "total_credit_amount": purchase_agg.total_credit if purchase_agg else Decimal("0.0000"),
        "total_suppliers": supplier_agg.total_suppliers if supplier_agg else 0,
        "total_payable": supplier_agg.total_payable if supplier_agg else Decimal("0.0000")
    }
