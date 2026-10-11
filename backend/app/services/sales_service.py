import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from fastapi import HTTPException, status

from app.models.business import Warehouse, Branch
from app.models.customer import Customer, CustomerLedgerEntry
from app.models.inventory import Product, InventoryBalance, StockMovement
from app.models.sales import Sale, SaleItem, Payment
from app.models.user import User
from app.schemas.sales import SaleCreate, SaleResponse, SaleItemResponse, PaymentResponse
from app.services.inventory_service import get_default_warehouse

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def generate_invoice_number(db: Session, business_id: uuid.UUID) -> str:
    """Generates a sequential human-readable invoice identifier: INV-YYYYMMDD-XXXX."""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"INV-{today_str}-"

    count_today = (
        db.query(func.count(Sale.id))
        .filter(Sale.business_id == business_id, Sale.invoice_number.like(f"{prefix}%"))
        .scalar()
    ) or 0

    seq = count_today + 1
    invoice_number = f"{prefix}{seq:04d}"

    # Handle rare collision
    collision = (
        db.query(Sale)
        .filter(Sale.business_id == business_id, Sale.invoice_number == invoice_number)
        .first()
    )
    while collision:
        seq += 1
        invoice_number = f"{prefix}{seq:04d}"
        collision = (
            db.query(Sale)
            .filter(Sale.business_id == business_id, Sale.invoice_number == invoice_number)
            .first()
        )

    return invoice_number


def _format_sale_response(sale: Sale) -> dict:
    """Helper to convert Sale ORM object into a dictionary compatible with SaleResponse schema."""
    items = []
    for it in sale.items:
        items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": it.product_name,
            "sku": it.sku,
            "unit": it.unit,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "discount_amount": it.discount_amount,
            "total_price": it.total_price,
            "unit_cost": it.unit_cost,
            "line_cogs": it.line_cogs,
        })

    payments = []
    for p in sale.payments:
        payments.append({
            "id": p.id,
            "payment_mode": p.payment_mode,
            "amount": p.amount,
            "notes": p.notes,
            "created_at": p.created_at,
        })

    return {
        "id": sale.id,
        "business_id": sale.business_id,
        "invoice_number": sale.invoice_number,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer.name if sale.customer else None,
        "customer_phone": sale.customer.phone if sale.customer else None,
        "status": sale.status,
        "subtotal_amount": sale.subtotal_amount,
        "discount_amount": sale.discount_amount,
        "tax_amount": sale.tax_amount,
        "total_amount": sale.total_amount,
        "paid_amount": sale.paid_amount,
        "credit_amount": sale.credit_amount,
        "cogs_total": sale.cogs_total,
        "payment_method": sale.payment_method,
        "payment_status": sale.payment_status,
        "notes": sale.notes,
        "created_by_user_id": sale.created_by_user_id,
        "created_by_user_name": sale.created_by_user.full_name if sale.created_by_user else None,
        "created_at": sale.created_at,
        "items": items,
        "payments": payments,
    }


def create_sale(
    db: Session,
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: SaleCreate
) -> dict:
    """
    Executes an atomic sales checkout transaction in PostgreSQL:
    1. Idempotency control: Returns existing sale if idempotency_key was already processed.
    2. Sorts product IDs deterministically to lock InventoryBalances with with_for_update() (deadlock prevention).
    3. Validates stock availability; strictly rolls back on insufficient stock.
    4. Calculates line totals and discounts on the backend using Decimal arithmetic. Never trusts frontend amounts.
    5. Calculates Moving Average Cost (MAC) snapshot for each line and total COGS.
    6. Deducts stock balances and records detailed StockMovement history.
    7. Validates payment modes (Cash, UPI, Card, Split, Credit).
    8. If credit is extended, checks customer credit limits, updates customer balance, and inserts Khata ledger entry.
    9. Commits the transaction atomically.
    """
    # 1. Idempotency check
    if req.idempotency_key:
        clean_key = req.idempotency_key.strip()
        existing_sale = (
            db.query(Sale)
            .filter(Sale.business_id == business_id, Sale.idempotency_key == clean_key)
            .first()
        )
        if existing_sale:
            return _format_sale_response(existing_sale)

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
                detail={"code": "PRODUCT_INACTIVE", "message": f"Product '{prod.name}' is inactive and cannot be sold."}
            )

    # Validate stock availability
    for p_id, requested_qty in product_qty_map.items():
        balance = balance_map.get(p_id)
        cur_stock = balance.current_stock if balance else Decimal("0.0000")
        if cur_stock < requested_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INSUFFICIENT_STOCK",
                    "message": f"Insufficient stock for '{prod_map[p_id].name}'. Requested: {requested_qty} {prod_map[p_id].unit}, Available: {cur_stock} {prod_map[p_id].unit}.",
                    "product_id": str(p_id),
                    "product_name": prod_map[p_id].name,
                    "requested": str(requested_qty),
                    "available": str(cur_stock)
                }
            )

    # 5. Calculate line items, prices, discounts and COGS
    subtotal = Decimal("0.0000")
    total_cogs = Decimal("0.0000")
    line_records: List[SaleItem] = []

    for item in req.items:
        prod = prod_map[item.product_id]
        bal = balance_map[item.product_id]
        qty = item.quantity.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        unit_price = prod.selling_price.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        line_sub = (qty * unit_price).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
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

        # Snapshot unit cost from moving average cost (or purchase cost fallback)
        unit_cost = (bal.average_cost if bal.average_cost > Decimal("0.0000") else prod.purchase_cost).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        line_cogs = (qty * unit_cost).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        total_cogs += line_cogs

        sale_item = SaleItem(
            product_id=prod.id,
            product_name=prod.name,
            sku=prod.sku,
            unit=prod.unit,
            quantity=qty,
            unit_price=unit_price,
            discount_amount=line_disc,
            total_price=line_tot,
            unit_cost=unit_cost,
            line_cogs=line_cogs
        )
        line_records.append(sale_item)

    # 6. Overall Sale Discount & Final Amount
    overall_discount = req.discount_amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    if overall_discount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_OVERALL_DISCOUNT", "message": "Overall discount cannot exceed sale subtotal."}
        )
    total_amount = (subtotal - overall_discount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    # 7. Customer validation
    customer = None
    if req.customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.id == req.customer_id, Customer.business_id == business_id)
            .with_for_update()
            .first()
        )
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CUSTOMER_NOT_FOUND", "message": "Specified customer does not exist."}
            )
        if not customer.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CUSTOMER_INACTIVE", "message": "Specified customer is inactive."}
            )

    # 8. Payment calculation and verification
    payment_records: List[Payment] = []
    paid_amount = Decimal("0.0000")
    credit_amount = Decimal("0.0000")

    if req.payment_method in ("cash", "upi", "card"):
        # If paid_amount not explicitly specified, assume fully paid
        if req.paid_amount is None:
            paid_amount = total_amount
        else:
            paid_amount = req.paid_amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        if paid_amount > total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OVERPAID", "message": "Paid amount cannot exceed total sale amount."}
            )

        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if credit_amount > Decimal("0.0000") and not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CUSTOMER_REQUIRED_FOR_CREDIT",
                    "message": "Partial payment creates a credit balance; please associate a customer."
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
                customer_id=customer.id if customer else None,
                payment_direction="inflow",
                payment_mode=req.payment_method,
                amount=paid_amount,
                notes=f"Payment for sale",
                created_by_user_id=user_id
            ))

    elif req.payment_method == "credit":
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CUSTOMER_REQUIRED_FOR_CREDIT", "message": "A customer is required for credit sales."}
            )

        paid_amount = (req.paid_amount or Decimal("0.0000")).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        if paid_amount > total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OVERPAID", "message": "Paid amount cannot exceed total sale amount."}
            )

        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        payment_status = "unpaid" if paid_amount == Decimal("0.0000") else ("partial" if paid_amount < total_amount else "paid")

        if paid_amount > Decimal("0.0000"):
            payment_records.append(Payment(
                business_id=business_id,
                customer_id=customer.id,
                payment_direction="inflow",
                payment_mode="cash",
                amount=paid_amount,
                notes="Initial payment on credit sale",
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
                detail={"code": "OVERPAID", "message": f"Split payments total {split_sum} exceeds sale amount {total_amount}."}
            )

        paid_amount = split_sum
        credit_amount = (total_amount - paid_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

        if credit_amount > Decimal("0.0000") and not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CUSTOMER_REQUIRED_FOR_CREDIT", "message": "Customer required for remaining credit balance."}
            )

        payment_status = "paid" if credit_amount == Decimal("0.0000") else ("partial" if paid_amount > Decimal("0.0000") else "unpaid")

        for sp in req.split_payments:
            sp_amt = sp.amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            if sp_amt > Decimal("0.0000"):
                payment_records.append(Payment(
                    business_id=business_id,
                    customer_id=customer.id if customer else None,
                    payment_direction="inflow",
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

    # 9. Validate Customer Credit Limit
    if credit_amount > Decimal("0.0000") and customer:
        if customer.credit_limit > Decimal("0.0000"):
            potential_balance = customer.current_balance + credit_amount
            if potential_balance > customer.credit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "CREDIT_LIMIT_EXCEEDED",
                        "message": f"Credit limit exceeded. Current balance: {customer.current_balance}, new credit: {credit_amount}, limit: {customer.credit_limit}."
                    }
                )

    # 10. Generate Invoice Number
    invoice_number = generate_invoice_number(db, business_id)

    try:
        # 11. Create Sale entity
        sale = Sale(
            business_id=business_id,
            branch_id=branch_id,
            warehouse_id=warehouse.id,
            customer_id=customer.id if customer else None,
            invoice_number=invoice_number,
            idempotency_key=req.idempotency_key.strip() if req.idempotency_key else None,
            status="completed",
            subtotal_amount=subtotal,
            discount_amount=overall_discount,
            tax_amount=Decimal("0.0000"),
            total_amount=total_amount,
            paid_amount=paid_amount,
            credit_amount=credit_amount,
            cogs_total=total_cogs,
            payment_method=req.payment_method,
            payment_status=payment_status,
            notes=req.notes.strip() if req.notes else None,
            created_by_user_id=user_id
        )
        db.add(sale)
        db.flush()

        # 12. Add Sale Items
        for item_rec in line_records:
            item_rec.sale_id = sale.id
            db.add(item_rec)

        # 13. Deduct stock balances and log StockMovement
        for p_id, requested_qty in product_qty_map.items():
            bal = balance_map[p_id]
            bal.current_stock -= requested_qty
            unit_cost = bal.average_cost if bal.average_cost > Decimal("0.0000") else prod_map[p_id].purchase_cost

            movement = StockMovement(
                business_id=business_id,
                warehouse_id=warehouse.id,
                product_id=p_id,
                movement_type="sale",
                quantity_delta=-requested_qty,
                balance_after=bal.current_stock,
                unit_cost=unit_cost,
                reason=f"Sale {invoice_number}",
                created_by_user_id=user_id
            )
            db.add(movement)

        # 14. Record Payments
        for pmt in payment_records:
            pmt.sale_id = sale.id
            db.add(pmt)

        # 15. If credit amount, update Customer Khata & record Ledger entry
        if credit_amount > Decimal("0.0000") and customer:
            new_customer_balance = (customer.current_balance + credit_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
            customer.current_balance = new_customer_balance

            ledger_entry = CustomerLedgerEntry(
                business_id=business_id,
                customer_id=customer.id,
                entry_type="credit_sale",
                reference_id=sale.id,
                amount=credit_amount,
                balance_after=new_customer_balance,
                notes=f"Credit for invoice {invoice_number}",
                created_by_user_id=user_id
            )
            db.add(ledger_entry)

        # 16. Commit single PostgreSQL transaction
        db.commit()
        db.refresh(sale)

        return _format_sale_response(sale)
    except Exception:
        db.rollback()
        raise



def get_sale_detail(
    db: Session,
    business_id: uuid.UUID,
    sale_id: uuid.UUID
) -> dict:
    """Fetches completed sale details including line items and payment transactions."""
    sale = (
        db.query(Sale)
        .filter(Sale.id == sale_id, Sale.business_id == business_id)
        .first()
    )
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SALE_NOT_FOUND", "message": "Sale transaction not found."}
        )

    return _format_sale_response(sale)


def list_sales(
    db: Session,
    business_id: uuid.UUID,
    search: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    payment_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[dict], int]:
    """Lists sales invoices with pagination and search."""
    query = (
        db.query(Sale)
        .filter(Sale.business_id == business_id)
    )

    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)

    if payment_status:
        query = query.filter(Sale.payment_status == payment_status)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.outerjoin(Customer, Customer.id == Sale.customer_id).filter(
            or_(
                func.lower(Sale.invoice_number).ilike(s),
                func.lower(Customer.name).ilike(s),
                Customer.phone.ilike(s)
            )
        )

    total_count = query.count()
    sales = query.order_by(Sale.created_at.desc()).offset(offset).limit(limit).all()

    return [_format_sale_response(s) for s in sales], total_count


def get_sales_overview(db: Session, business_id: uuid.UUID) -> dict:
    """Aggregates sales metrics (total volume, revenue, credit, COGS, receivables)."""
    sales_agg = (
        db.query(
            func.count(Sale.id).label("total_count"),
            func.coalesce(func.sum(Sale.total_amount), Decimal("0.0000")).label("total_amount"),
            func.coalesce(func.sum(Sale.paid_amount), Decimal("0.0000")).label("total_paid"),
            func.coalesce(func.sum(Sale.credit_amount), Decimal("0.0000")).label("total_credit"),
            func.coalesce(func.sum(Sale.cogs_total), Decimal("0.0000")).label("total_cogs")
        )
        .filter(Sale.business_id == business_id, Sale.status == "completed")
        .first()
    )

    customer_agg = (
        db.query(
            func.count(Customer.id).label("total_customers"),
            func.coalesce(func.sum(Customer.current_balance), Decimal("0.0000")).label("total_receivable")
        )
        .filter(Customer.business_id == business_id, Customer.is_active == True)
        .first()
    )

    return {
        "total_sales_count": sales_agg.total_count if sales_agg else 0,
        "total_sales_amount": sales_agg.total_amount if sales_agg else Decimal("0.0000"),
        "total_paid_amount": sales_agg.total_paid if sales_agg else Decimal("0.0000"),
        "total_credit_amount": sales_agg.total_credit if sales_agg else Decimal("0.0000"),
        "total_cogs": sales_agg.total_cogs if sales_agg else Decimal("0.0000"),
        "total_customers": customer_agg.total_customers if customer_agg else 0,
        "total_receivable": customer_agg.total_receivable if customer_agg else Decimal("0.0000")
    }
