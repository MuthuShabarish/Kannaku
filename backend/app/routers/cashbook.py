from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.cashbook import CashbookTransactionResponse, CashbookSummaryResponse
from app.services.cashbook_service import (
    get_cashbook_transactions,
    get_cashbook_summary
)

router = APIRouter(prefix="/api/v1/cashbook", tags=["Operating Cashbook"])


@router.get("/transactions", response_model=ApiResponse[List[CashbookTransactionResponse]])
def get_cashbook_transactions_endpoint(
    start_date: Optional[datetime] = Query(None, description="Filter from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date"),
    direction: Optional[str] = Query(None, description="inflow or outflow"),
    payment_mode: Optional[str] = Query(None, description="cash, upi, card, or bank_transfer"),
    source_type: Optional[str] = Query(None, description="sale_payment, customer_settlement, purchase_payment, supplier_settlement, operating_expense"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns unified chronological cashbook transactions derived directly from
    authoritative sales, customer collections, purchases, supplier payments, and operating expenses.
    """
    transactions, total_count = get_cashbook_transactions(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date,
        direction=direction,
        payment_mode=payment_mode,
        source_type=source_type,
        limit=limit,
        offset=offset
    )

    return ApiResponse(
        data=transactions,
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/summary", response_model=ApiResponse[CashbookSummaryResponse])
def get_cashbook_summary_endpoint(
    start_date: Optional[datetime] = Query(None, description="Filter from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated period cashbook metrics: Total Inflows, Total Outflows,
    Net Cash Movement, and Breakdown by payment mode without double-counting.
    """
    summary = get_cashbook_summary(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse(data=summary)
