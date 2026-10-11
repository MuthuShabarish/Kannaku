from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.reports import (
    BusinessSummaryReportResponse,
    SalesTrendsReportResponse,
    ProductSalesReportResponse,
    ProfitOverviewReportResponse
)
from app.services.reporting_service import (
    get_business_summary_report,
    get_sales_trends_report,
    get_product_sales_report,
    get_profit_overview_report
)

router = APIRouter(prefix="/api/v1/reports", tags=["Business Reports & Profit"])


@router.get("/summary", response_model=ApiResponse[BusinessSummaryReportResponse])
def get_business_summary_endpoint(
    start_date: Optional[datetime] = Query(None, description="Start date/time for reporting period"),
    end_date: Optional[datetime] = Query(None, description="End date/time for reporting period"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns comprehensive business summary for the requested date range:
    Sales revenue, Invoices, Purchases, Expenses, Gross & Operating Profit estimates, and Cash movements.
    """
    data = get_business_summary_report(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse(data=data)


@router.get("/sales-trends", response_model=ApiResponse[SalesTrendsReportResponse])
def get_sales_trends_endpoint(
    start_date: Optional[datetime] = Query(None, description="Start date/time"),
    end_date: Optional[datetime] = Query(None, description="End date/time"),
    interval: str = Query("day", pattern="^(day|month)$", description="Bucket interval: day or month"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns periodic sales trends (daily or monthly) with revenue, invoice count, COGS, and gross profit.
    """
    data = get_sales_trends_report(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )
    return ApiResponse(data=data)


@router.get("/product-sales", response_model=ApiResponse[ProductSalesReportResponse])
def get_product_sales_endpoint(
    start_date: Optional[datetime] = Query(None, description="Start date/time"),
    end_date: Optional[datetime] = Query(None, description="End date/time"),
    limit: int = Query(10, ge=1, le=100, description="Number of top products to return"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns product-level performance rankings by revenue and quantity sold, plus category breakdowns.
    """
    data = get_product_sales_report(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return ApiResponse(data=data)


@router.get("/profit-overview", response_model=ApiResponse[ProfitOverviewReportResponse])
def get_profit_overview_endpoint(
    start_date: Optional[datetime] = Query(None, description="Start date/time"),
    end_date: Optional[datetime] = Query(None, description="End date/time"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns transparent profit overview contrasting Gross & Operating profit against net cash movements,
    with expense category breakdowns and explicit accounting disclosures.
    """
    data = get_profit_overview_report(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse(data=data)
