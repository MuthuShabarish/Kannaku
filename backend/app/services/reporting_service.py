import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, timezone, time, date
from typing import Optional, List, Tuple, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc

from app.models.business import Business
from app.models.sales import Sale, SaleItem
from app.models.purchase import Purchase
from app.models.expense import Expense, ExpenseCategory
from app.models.inventory import Product, Category
from app.services.cashbook_service import get_cashbook_summary
from app.schemas.reports import (
    PeriodSummary,
    SalesMetrics,
    PurchaseMetrics,
    ExpenseMetrics,
    ProfitMetrics,
    CashMovementMetrics,
    BusinessSummaryReportResponse,
    SalesTrendPoint,
    SalesTrendsReportResponse,
    ProductPerformance,
    CategoryPerformance,
    ProductSalesReportResponse,
    ProfitOverviewReportResponse
)

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def get_business_timezone(db: Session, business_id: uuid.UUID) -> str:
    """Retrieves configured timezone from business settings, defaulting to Asia/Kolkata."""
    biz = db.query(Business).filter(Business.id == business_id).first()
    if biz and biz.settings and isinstance(biz.settings, dict):
        tz = biz.settings.get("timezone")
        if tz:
            return tz
    return "Asia/Kolkata"


def resolve_period_bounds(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    timezone_name: str = "Asia/Kolkata"
) -> Tuple[Optional[datetime], Optional[datetime], ZoneInfo]:
    """
    Standardizes start and end timestamps into UTC boundaries based on business timezone.
    If naive date/datetime is provided, it is interpreted in business timezone and converted to UTC.
    """
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    start_utc = None
    end_utc = None

    if start_date:
        if start_date.tzinfo is None:
            # Assume local business time
            start_local = start_date.replace(tzinfo=tz)
            start_utc = start_local.astimezone(timezone.utc)
        else:
            start_utc = start_date.astimezone(timezone.utc)

    if end_date:
        if end_date.tzinfo is None:
            # If time is 00:00:00, extend to end of day 23:59:59.999999
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0 and end_date.microsecond == 0:
                end_date_eod = datetime.combine(end_date.date(), time(23, 59, 59, 999999))
                end_local = end_date_eod.replace(tzinfo=tz)
            else:
                end_local = end_date.replace(tzinfo=tz)
            end_utc = end_local.astimezone(timezone.utc)
        else:
            end_utc = end_date.astimezone(timezone.utc)

    return start_utc, end_utc, tz


def get_business_summary_report(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> BusinessSummaryReportResponse:
    """
    Computes unified business performance metrics across sales, purchases, expenses,
    profitability and cashbook movements for the requested period.
    """
    tz_str = get_business_timezone(db, business_id)
    start_utc, end_utc, tz = resolve_period_bounds(start_date, end_date, tz_str)

    # 1. Sales Metrics (completed only)
    sales_filter = [
        Sale.business_id == business_id,
        Sale.status == "completed"
    ]
    if start_utc:
        sales_filter.append(Sale.created_at >= start_utc)
    if end_utc:
        sales_filter.append(Sale.created_at <= end_utc)

    sales_stmt = select(
        func.coalesce(func.sum(Sale.total_amount), Decimal("0.0000")),
        func.coalesce(func.sum(Sale.subtotal_amount), Decimal("0.0000")),
        func.coalesce(func.sum(Sale.discount_amount), Decimal("0.0000")),
        func.coalesce(func.sum(Sale.tax_amount), Decimal("0.0000")),
        func.count(Sale.id),
        func.coalesce(func.sum(Sale.cogs_total), Decimal("0.0000"))
    ).filter(*sales_filter)

    total_revenue, gross_sales, discounts, tax, invoice_count, cogs_total = db.execute(sales_stmt).one()

    avg_invoice = (total_revenue / Decimal(invoice_count)).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN) if invoice_count > 0 else Decimal("0.0000")

    sales_metrics = SalesMetrics(
        total_revenue=total_revenue,
        gross_sales=gross_sales,
        discounts=discounts,
        tax=tax,
        invoice_count=invoice_count,
        average_invoice_value=avg_invoice
    )

    # 2. Purchases Metrics (non-cancelled only)
    pur_filter = [
        Purchase.business_id == business_id,
        Purchase.status != "cancelled"
    ]
    if start_utc:
        pur_filter.append(Purchase.purchase_date >= start_utc)
    if end_utc:
        pur_filter.append(Purchase.purchase_date <= end_utc)

    pur_stmt = select(
        func.coalesce(func.sum(Purchase.total_amount), Decimal("0.0000")),
        func.count(Purchase.id)
    ).filter(*pur_filter)

    total_purchases, purchase_count = db.execute(pur_stmt).one()
    purchase_metrics = PurchaseMetrics(
        total_purchases=total_purchases,
        purchase_count=purchase_count
    )

    # 3. Expenses Metrics (breakdown by status)
    exp_filter = [Expense.business_id == business_id]
    if start_utc:
        exp_filter.append(Expense.expense_date >= start_utc)
    if end_utc:
        exp_filter.append(Expense.expense_date <= end_utc)

    # Paid expenses (active)
    paid_stmt = select(
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
        func.count(Expense.id)
    ).filter(
        *exp_filter,
        Expense.payment_status == "paid",
        Expense.voided_at.is_(None)
    )
    paid_amount, paid_count = db.execute(paid_stmt).one()

    # Unpaid expenses
    unpaid_stmt = select(
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
        func.count(Expense.id)
    ).filter(
        *exp_filter,
        Expense.payment_status == "unpaid",
        Expense.voided_at.is_(None)
    )
    unpaid_amount, unpaid_count = db.execute(unpaid_stmt).one()

    # Voided expenses
    voided_stmt = select(
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
        func.count(Expense.id)
    ).filter(
        *exp_filter,
        func.coalesce(Expense.payment_status, "") == "voided"
    )
    voided_amount, _ = db.execute(voided_stmt).one()

    total_active_expenses = paid_amount + unpaid_amount
    expense_metrics = ExpenseMetrics(
        total_expenses=total_active_expenses,
        paid_expenses=paid_amount,
        unpaid_expenses=unpaid_amount,
        voided_expenses=voided_amount,
        expense_count=paid_count + unpaid_count
    )

    # 4. Profit Overview
    gross_profit = total_revenue - cogs_total
    gross_margin_pct = (
        ((gross_profit / total_revenue) * Decimal("100.00")).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
        if total_revenue > Decimal("0.0000") else Decimal("0.00")
    )

    # Operating expenses under documented operational rule = paid expenses
    operating_profit_estimate = gross_profit - paid_amount
    op_margin_pct = (
        ((operating_profit_estimate / total_revenue) * Decimal("100.00")).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
        if total_revenue > Decimal("0.0000") else Decimal("0.00")
    )

    profit_metrics = ProfitMetrics(
        sales_revenue=total_revenue,
        cogs_total=cogs_total,
        gross_profit=gross_profit,
        gross_profit_margin_pct=gross_margin_pct,
        operating_expenses=paid_amount,
        operating_profit_estimate=operating_profit_estimate,
        operating_profit_margin_pct=op_margin_pct
    )

    # 5. Cash Movement Metrics from Cashbook
    cash_summary = get_cashbook_summary(
        db=db,
        business_id=business_id,
        start_date=start_utc,
        end_date=end_utc
    )
    cash_metrics = CashMovementMetrics(
        total_inflows=cash_summary.total_inflows,
        total_outflows=cash_summary.total_outflows,
        net_cash_movement=cash_summary.net_cash_movement
    )

    disclosures = [
        "Sales revenue reflects completed invoices. Khata credit collections are cash liquidity settlements, not new revenue.",
        "COGS reflects historical inventory cost snapshots at the time of each sale, not current replacement cost.",
        "Inventory purchases are capitalized into stock and flow through COGS when sold; they are not double-counted as operating expenses.",
        "Operating profit is an operational estimate (Gross Profit - Paid Operating Expenses), distinct from net cash movement."
    ]

    is_empty = (invoice_count == 0 and purchase_count == 0 and (paid_count + unpaid_count) == 0)

    period_summary = PeriodSummary(
        start_date=start_utc,
        end_date=end_utc,
        timezone=tz_str,
        is_empty_range=is_empty
    )

    return BusinessSummaryReportResponse(
        period=period_summary,
        sales=sales_metrics,
        purchases=purchase_metrics,
        expenses=expense_metrics,
        profit=profit_metrics,
        cash_movement=cash_metrics,
        disclosures=disclosures
    )


def get_sales_trends_report(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: str = "day"
) -> SalesTrendsReportResponse:
    """
    Computes periodic sales trend buckets (daily or monthly), grouping by business-local time.
    """
    tz_str = get_business_timezone(db, business_id)
    start_utc, end_utc, tz = resolve_period_bounds(start_date, end_date, tz_str)

    sales_filter = [
        Sale.business_id == business_id,
        Sale.status == "completed"
    ]
    if start_utc:
        sales_filter.append(Sale.created_at >= start_utc)
    if end_utc:
        sales_filter.append(Sale.created_at <= end_utc)

    sales = (
        db.query(Sale.created_at, Sale.total_amount, Sale.cogs_total)
        .filter(*sales_filter)
        .order_by(Sale.created_at.asc())
        .all()
    )

    format_str = "%Y-%m-%d" if interval.lower() == "day" else "%Y-%m"
    buckets: Dict[str, Dict[str, Any]] = {}

    for s_created_at, s_total, s_cogs in sales:
        # Convert UTC timestamp to business local date key
        local_dt = s_created_at.astimezone(tz)
        key = local_dt.strftime(format_str)

        if key not in buckets:
            buckets[key] = {
                "sales_revenue": Decimal("0.0000"),
                "invoice_count": 0,
                "cogs_total": Decimal("0.0000")
            }
        buckets[key]["sales_revenue"] += s_total
        buckets[key]["invoice_count"] += 1
        buckets[key]["cogs_total"] += s_cogs

    trend_points: List[SalesTrendPoint] = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        gp = b["sales_revenue"] - b["cogs_total"]
        trend_points.append(
            SalesTrendPoint(
                date_key=key,
                sales_revenue=b["sales_revenue"],
                invoice_count=b["invoice_count"],
                cogs_total=b["cogs_total"],
                gross_profit=gp
            )
        )

    period_summary = PeriodSummary(
        start_date=start_utc,
        end_date=end_utc,
        timezone=tz_str,
        is_empty_range=(len(trend_points) == 0)
    )

    return SalesTrendsReportResponse(
        period=period_summary,
        interval=interval.lower(),
        trends=trend_points
    )


def get_product_sales_report(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10
) -> ProductSalesReportResponse:
    """
    Computes product sales and category insights from completed sale item snapshots.
    """
    tz_str = get_business_timezone(db, business_id)
    start_utc, end_utc, _ = resolve_period_bounds(start_date, end_date, tz_str)

    base_filter = [
        Sale.business_id == business_id,
        Sale.status == "completed"
    ]
    if start_utc:
        base_filter.append(Sale.created_at >= start_utc)
    if end_utc:
        base_filter.append(Sale.created_at <= end_utc)

    # 1. Product-level Aggregation
    prod_stmt = (
        select(
            SaleItem.product_id,
            SaleItem.product_name,
            SaleItem.unit,
            Category.name.label("category_name"),
            func.coalesce(func.sum(SaleItem.quantity), Decimal("0.0000")),
            func.coalesce(func.sum(SaleItem.total_price), Decimal("0.0000")),
            func.coalesce(func.sum(SaleItem.line_cogs), Decimal("0.0000"))
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .outerjoin(Product, SaleItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .filter(*base_filter)
        .group_by(
            SaleItem.product_id,
            SaleItem.product_name,
            SaleItem.unit,
            Category.name
        )
    )

    prod_rows = db.execute(prod_stmt).all()

    items: List[ProductPerformance] = []
    for p_id, p_name, p_unit, c_name, qty, rev, cogs in prod_rows:
        gp = rev - cogs
        margin = (
            ((gp / rev) * Decimal("100.00")).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
            if rev > Decimal("0.0000") else Decimal("0.00")
        )
        items.append(
            ProductPerformance(
                product_id=p_id,
                product_name=p_name,
                category_name=c_name,
                unit=p_unit,
                quantity_sold=qty,
                revenue=rev,
                cogs=cogs,
                gross_profit=gp,
                margin_pct=margin
            )
        )

    top_by_rev = sorted(items, key=lambda x: x.revenue, reverse=True)[:limit]
    top_by_qty = sorted(items, key=lambda x: x.quantity_sold, reverse=True)[:limit]

    # 2. Category-level Aggregation
    cat_stmt = (
        select(
            Product.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            func.coalesce(func.sum(SaleItem.quantity), Decimal("0.0000")),
            func.coalesce(func.sum(SaleItem.total_price), Decimal("0.0000")),
            func.coalesce(func.sum(SaleItem.line_cogs), Decimal("0.0000"))
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .outerjoin(Product, SaleItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .filter(*base_filter)
        .group_by(Product.category_id, Category.name)
        .order_by(desc(func.sum(SaleItem.total_price)))
    )

    cat_rows = db.execute(cat_stmt).all()
    by_category: List[CategoryPerformance] = []
    for c_id, c_name, qty, rev, cogs in cat_rows:
        gp = rev - cogs
        by_category.append(
            CategoryPerformance(
                category_id=c_id,
                category_name=c_name,
                quantity_sold=qty,
                revenue=rev,
                cogs=cogs,
                gross_profit=gp
            )
        )

    period_summary = PeriodSummary(
        start_date=start_utc,
        end_date=end_utc,
        timezone=tz_str,
        is_empty_range=(len(items) == 0)
    )

    return ProductSalesReportResponse(
        period=period_summary,
        top_by_revenue=top_by_rev,
        top_by_quantity=top_by_qty,
        by_category=by_category
    )


def get_profit_overview_report(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> ProfitOverviewReportResponse:
    """
    Computes transparent profit overview, contrasting operational profit estimate with
    net cash flow, detailing expense categories and status distributions.
    """
    summary = get_business_summary_report(db, business_id, start_date, end_date)
    start_utc, end_utc, _ = resolve_period_bounds(start_date, end_date, summary.period.timezone)

    # Detailed Expense Category breakdown
    exp_filter = [
        Expense.business_id == business_id,
        Expense.payment_status == "paid",
        Expense.voided_at.is_(None)
    ]
    if start_utc:
        exp_filter.append(Expense.expense_date >= start_utc)
    if end_utc:
        exp_filter.append(Expense.expense_date <= end_utc)

    cat_stmt = (
        select(
            ExpenseCategory.id,
            ExpenseCategory.name,
            func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
            func.count(Expense.id)
        )
        .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
        .filter(*exp_filter)
        .group_by(ExpenseCategory.id, ExpenseCategory.name)
        .order_by(desc(func.sum(Expense.amount)))
    )

    cat_rows = db.execute(cat_stmt).all()
    expense_cats = [
        {
            "category_id": str(row[0]),
            "category_name": row[1],
            "amount": row[2],
            "count": row[3]
        }
        for row in cat_rows
    ]

    status_breakdown = {
        "paid": summary.expenses.paid_expenses,
        "unpaid": summary.expenses.unpaid_expenses,
        "voided": summary.expenses.voided_expenses
    }

    profit_vs_cash_gap = summary.profit.operating_profit_estimate - summary.cash_movement.net_cash_movement

    accounting_rules = {
        "sales_revenue": "Total value of completed sales invoices within the period. Excludes cancelled bills. Khata credit collections do not increase sales revenue.",
        "cogs": "Cost of goods sold based strictly on moving-average unit costs snapshotted on sale items at the moment of sale. Never recalculated from current replacement cost.",
        "gross_profit": "Sales Revenue minus Cost of Goods Sold.",
        "operating_expenses": "Paid business running costs (rent, wages, utilities, tea). Inventory purchases are capitalized in stock, not treated as expenses.",
        "operating_profit_estimate": "Gross Profit minus Paid Operating Expenses. Labeled as an operational estimate because the expense model records vouchers rather than an independent accrual liability ledger.",
        "profit_vs_cash": "Profitability measures economic value generated; cash movement tracks physical and digital liquidity timing."
    }

    return ProfitOverviewReportResponse(
        period=summary.period,
        profit=summary.profit,
        cash_movement=summary.cash_movement,
        profit_vs_cash_gap=profit_vs_cash_gap,
        expense_breakdown_by_category=expense_cats,
        expense_breakdown_by_status=status_breakdown,
        accounting_rules=accounting_rules
    )
