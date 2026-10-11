import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class PeriodSummary(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: str = "Asia/Kolkata"
    is_empty_range: bool = False


class SalesMetrics(BaseModel):
    total_revenue: Decimal
    gross_sales: Decimal
    discounts: Decimal
    tax: Decimal
    invoice_count: int
    average_invoice_value: Decimal


class PurchaseMetrics(BaseModel):
    total_purchases: Decimal
    purchase_count: int


class ExpenseMetrics(BaseModel):
    total_expenses: Decimal
    paid_expenses: Decimal
    unpaid_expenses: Decimal
    voided_expenses: Decimal
    expense_count: int


class ProfitMetrics(BaseModel):
    sales_revenue: Decimal
    cogs_total: Decimal
    gross_profit: Decimal
    gross_profit_margin_pct: Decimal
    operating_expenses: Decimal  # Paid operating expenses included in operational profit estimate
    operating_profit_estimate: Decimal  # gross_profit - operating_expenses
    operating_profit_margin_pct: Decimal


class CashMovementMetrics(BaseModel):
    total_inflows: Decimal
    total_outflows: Decimal
    net_cash_movement: Decimal


class BusinessSummaryReportResponse(BaseModel):
    period: PeriodSummary
    sales: SalesMetrics
    purchases: PurchaseMetrics
    expenses: ExpenseMetrics
    profit: ProfitMetrics
    cash_movement: CashMovementMetrics
    disclosures: List[str]


class SalesTrendPoint(BaseModel):
    date_key: str  # YYYY-MM-DD or YYYY-MM
    sales_revenue: Decimal
    invoice_count: int
    cogs_total: Decimal
    gross_profit: Decimal


class SalesTrendsReportResponse(BaseModel):
    period: PeriodSummary
    interval: str  # 'day' or 'month'
    trends: List[SalesTrendPoint]


class ProductPerformance(BaseModel):
    product_id: uuid.UUID
    product_name: str
    category_name: Optional[str] = None
    unit: str
    quantity_sold: Decimal
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    margin_pct: Decimal


class CategoryPerformance(BaseModel):
    category_id: Optional[uuid.UUID] = None
    category_name: str
    quantity_sold: Decimal
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal


class ProductSalesReportResponse(BaseModel):
    period: PeriodSummary
    top_by_revenue: List[ProductPerformance]
    top_by_quantity: List[ProductPerformance]
    by_category: List[CategoryPerformance]


class ProfitOverviewReportResponse(BaseModel):
    period: PeriodSummary
    profit: ProfitMetrics
    cash_movement: CashMovementMetrics
    profit_vs_cash_gap: Decimal  # operating_profit_estimate - net_cash_movement
    expense_breakdown_by_category: List[Dict[str, Any]]
    expense_breakdown_by_status: Dict[str, Decimal]
    accounting_rules: Dict[str, str]
