import uuid
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.cash_closing import (
    CurrentDrawerStatusResponse,
    CashClosingCreate,
    CashClosingResponse,
    CashClosingReopenRequest,
    CashLegBreakdown
)
from app.services.cash_closing_service import (
    get_current_drawer_status,
    close_cash_drawer,
    reopen_cash_closing,
    get_cash_closing_history,
    get_cash_closing_detail
)

router = APIRouter(prefix="/api/v1/cash-closing", tags=["Daily Cash Drawer Closing"])


@router.get("/current", response_model=ApiResponse[CurrentDrawerStatusResponse])
def get_current_drawer_endpoint(
    closing_date: Optional[date] = Query(None, description="Target business-local closing date (defaults to today)"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real-time physical cash drawer status, opening balance, cash inflows and outflows,
    and calculated expected closing cash. If drawer is already closed for the date, returns closed details.
    """
    status_data = get_current_drawer_status(
        db=db,
        business_id=current_business.id,
        target_date=closing_date
    )
    return ApiResponse(data=status_data)


@router.post("/close", response_model=ApiResponse[CashClosingResponse], status_code=status.HTTP_201_CREATED)
def close_cash_drawer_endpoint(
    req: CashClosingCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs atomic daily cash closing.
    Computes difference (Actual - Expected), locks against duplicates, and records immutable closed audit record.
    """
    closing_record = close_cash_drawer(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=closing_record,
        message="Daily physical cash drawer closed and reconciled successfully."
    )


@router.post("/{closing_id}/reopen", response_model=ApiResponse[CashClosingResponse])
def reopen_cash_drawer_endpoint(
    closing_id: uuid.UUID,
    req: CashClosingReopenRequest,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auditable reopening policy:
    Allows authorized reopening of a closed drawer session with a mandatory audit reason.
    """
    reopened = reopen_cash_closing(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        closing_id=closing_id,
        reason=req.reason
    )
    return ApiResponse(
        data=reopened,
        message="Cash closing session reopened for correction with audit logging."
    )


@router.get("/history", response_model=ApiResponse[List[CashClosingResponse]])
def get_cash_closing_history_endpoint(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological history of daily cash closings and reconciliation results.
    """
    records, total_count = get_cash_closing_history(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=records,
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/{closing_id}", response_model=ApiResponse[Dict[str, Any]])
def get_cash_closing_detail_endpoint(
    closing_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed breakdown of a specific closed session.
    """
    closing, breakdown = get_cash_closing_detail(
        db=db,
        business_id=current_business.id,
        closing_id=closing_id
    )
    return ApiResponse(
        data={
            "closing": closing,
            "breakdown": breakdown
        }
    )
