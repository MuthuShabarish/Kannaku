import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.models.sales import Payment, Sale
from app.models.customer import Customer
from app.models.purchase import Purchase
from app.models.supplier import Supplier
from app.models.expense import Expense, ExpenseCategory
from app.schemas.cashbook import CashbookTransactionResponse, CashbookSummaryResponse


def get_cashbook_transactions(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    direction: Optional[str] = None,
    payment_mode: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[CashbookTransactionResponse], int]:
    """
    Derives unified, non-duplicative cashbook transactions directly from:
    1. Payment records (Sales immediate tender, Customer settlements, Purchase tender, Supplier settlements)
    2. Expense records (Paid operating expenses)
    """
    items: List[CashbookTransactionResponse] = []

    # ----------------------------------------------------
    # 1. Fetch from authoritative Payment table
    # ----------------------------------------------------
    # Payment query
    pay_stmt = select(Payment).filter(Payment.business_id == business_id)
    if start_date:
        pay_stmt = pay_stmt.filter(Payment.created_at >= start_date)
    if end_date:
        pay_stmt = pay_stmt.filter(Payment.created_at <= end_date)
    if direction:
        pay_stmt = pay_stmt.filter(Payment.payment_direction == direction.lower())
    if payment_mode:
        pay_stmt = pay_stmt.filter(Payment.payment_mode == payment_mode.lower())

    payments = list(db.execute(pay_stmt).scalars().all())

    # Pre-cache related entity details to avoid N+1 queries
    sale_ids = [p.sale_id for p in payments if p.sale_id]
    customer_ids = [p.customer_id for p in payments if p.customer_id]
    purchase_ids = [p.purchase_id for p in payments if p.purchase_id]
    supplier_ids = [p.supplier_id for p in payments if p.supplier_id]

    sales_map = {}
    if sale_ids:
        sales = db.execute(select(Sale).filter(Sale.id.in_(sale_ids))).scalars().all()
        for s in sales:
            sales_map[s.id] = s
            if s.customer_id:
                customer_ids.append(s.customer_id)

    customers_map = {}
    if customer_ids:
        custs = db.execute(select(Customer).filter(Customer.id.in_(set(customer_ids)))).scalars().all()
        for c in custs:
            customers_map[c.id] = c

    purchases_map = {}
    if purchase_ids:
        purs = db.execute(select(Purchase).filter(Purchase.id.in_(purchase_ids))).scalars().all()
        for pr in purs:
            purchases_map[pr.id] = pr
            if pr.supplier_id:
                supplier_ids.append(pr.supplier_id)

    suppliers_map = {}
    if supplier_ids:
        sups = db.execute(select(Supplier).filter(Supplier.id.in_(set(supplier_ids)))).scalars().all()
        for sp in sups:
            suppliers_map[sp.id] = sp

    for p in payments:
        p_source_type = "unknown"
        category = "General Payment"
        ref = None
        party = None

        if p.sale_id:
            p_source_type = "sale_payment"
            category = "Sale Revenue"
            sale_obj = sales_map.get(p.sale_id)
            if sale_obj:
                ref = sale_obj.invoice_number
                if sale_obj.customer_id and sale_obj.customer_id in customers_map:
                    party = customers_map[sale_obj.customer_id].name
                else:
                    party = "Walk-in Customer"
        elif p.customer_id:
            p_source_type = "customer_settlement"
            category = "Customer Khata Collection"
            cust_obj = customers_map.get(p.customer_id)
            party = cust_obj.name if cust_obj else "Customer"
            ref = p.notes or "Khata Settlement"
        elif p.purchase_id:
            p_source_type = "purchase_payment"
            category = "Inventory Purchase"
            pur_obj = purchases_map.get(p.purchase_id)
            if pur_obj:
                ref = pur_obj.invoice_number
                if pur_obj.supplier_id and pur_obj.supplier_id in suppliers_map:
                    party = suppliers_map[pur_obj.supplier_id].name
                else:
                    party = "Supplier"
        elif p.supplier_id:
            p_source_type = "supplier_settlement"
            category = "Supplier AP Settlement"
            sup_obj = suppliers_map.get(p.supplier_id)
            party = sup_obj.name if sup_obj else "Supplier"
            ref = p.notes or "AP Settlement"

        if source_type and p_source_type != source_type.lower():
            continue

        items.append(
            CashbookTransactionResponse(
                id=f"pay-{p.id}",
                source_type=p_source_type,
                source_id=p.id,
                transaction_date=p.created_at,
                direction=p.payment_direction,
                amount=p.amount,
                payment_mode=p.payment_mode,
                category=category,
                reference=ref,
                party_name=party,
                description=p.notes
            )
        )

    # ----------------------------------------------------
    # 2. Fetch from authoritative Expense table
    # ----------------------------------------------------
    # Operating Expenses with status 'paid' are Outflows
    if direction is None or direction.lower() == "outflow":
        if source_type is None or source_type.lower() == "operating_expense":
            exp_stmt = select(Expense).filter(
                Expense.business_id == business_id,
                Expense.payment_status == "paid",
                Expense.voided_at.is_(None)
            )
            if start_date:
                exp_stmt = exp_stmt.filter(Expense.expense_date >= start_date)
            if end_date:
                exp_stmt = exp_stmt.filter(Expense.expense_date <= end_date)
            if payment_mode:
                exp_stmt = exp_stmt.filter(Expense.payment_method == payment_mode.lower())

            expenses = list(db.execute(exp_stmt).scalars().all())

            # Pre-cache category names
            exp_cat_ids = list(set([e.category_id for e in expenses]))
            cats_map = {}
            if exp_cat_ids:
                cats = db.execute(select(ExpenseCategory).filter(ExpenseCategory.id.in_(exp_cat_ids))).scalars().all()
                for c in cats:
                    cats_map[c.id] = c.name

            for e in expenses:
                items.append(
                    CashbookTransactionResponse(
                        id=f"exp-{e.id}",
                        source_type="operating_expense",
                        source_id=e.id,
                        transaction_date=e.expense_date,
                        direction="outflow",
                        amount=e.amount,
                        payment_mode=e.payment_method,
                        category=cats_map.get(e.category_id, "Operating Expense"),
                        reference=e.expense_number,
                        party_name=e.payee or "Operating Expense",
                        description=e.description
                    )
                )

    # ----------------------------------------------------
    # 3. Sort Chronologically & Paginate
    # ----------------------------------------------------
    items.sort(key=lambda x: x.transaction_date, reverse=True)
    total_count = len(items)
    paginated_items = items[offset:offset + limit]

    return paginated_items, total_count


def get_cashbook_summary(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> CashbookSummaryResponse:
    """
    Computes aggregated inflows, outflows, mode breakdowns, and net movement
    for the selected period.
    """
    transactions, total_count = get_cashbook_transactions(
        db=db,
        business_id=business_id,
        start_date=start_date,
        end_date=end_date,
        limit=100000,  # Uncapped for summary aggregation
        offset=0
    )

    total_inflows = Decimal("0.0000")
    total_outflows = Decimal("0.0000")
    inflows_by_mode: Dict[str, Decimal] = {}
    outflows_by_mode: Dict[str, Decimal] = {}

    for tx in transactions:
        mode = tx.payment_mode.lower()
        if tx.direction == "inflow":
            total_inflows += tx.amount
            inflows_by_mode[mode] = inflows_by_mode.get(mode, Decimal("0.0000")) + tx.amount
        elif tx.direction == "outflow":
            total_outflows += tx.amount
            outflows_by_mode[mode] = outflows_by_mode.get(mode, Decimal("0.0000")) + tx.amount

    net_movement = total_inflows - total_outflows

    return CashbookSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        total_inflows=total_inflows,
        total_outflows=total_outflows,
        net_cash_movement=net_movement,
        inflows_by_mode=inflows_by_mode,
        outflows_by_mode=outflows_by_mode,
        transaction_count=total_count
    )
