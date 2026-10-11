import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseResponse,
    PurchaseOverviewResponse
)
from app.services.purchase_service import (
    create_purchase,
    get_purchase_detail,
    list_purchases,
    get_purchases_overview
)

router = APIRouter(prefix="/api/v1/purchases", tags=["Purchase Billing & Receiving"])


@router.post("", response_model=ApiResponse[PurchaseResponse], status_code=status.HTTP_201_CREATED)
def create_purchase_endpoint(
    req: PurchaseCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes an atomic purchase receiving transaction:
    - Atomically receives stock and recalculates moving-average cost (MAC) with deadlock-safe locking.
    - Captures landed item costs with proportional invoice discount allocation.
    - Idempotency control via idempotency_key prevents duplicate stock receiving.
    - Updates Supplier AP balance if credit or partial payment is used.
    """
    purchase_data = create_purchase(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=PurchaseResponse(**purchase_data),
        message=f"Purchase received successfully. Invoice: {purchase_data['invoice_number']}."
    )


@router.get("/overview", response_model=ApiResponse[PurchaseOverviewResponse])
def get_purchases_overview_endpoint(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns aggregated purchase volume, amount, paid total, and supplier payables."""
    metrics = get_purchases_overview(db=db, business_id=current_business.id)
    return ApiResponse(data=PurchaseOverviewResponse(**metrics))


@router.get("", response_model=ApiResponse[List[PurchaseResponse]])
def list_purchases_endpoint(
    search: Optional[str] = Query(None, description="Search by invoice number, supplier invoice ref, or supplier name"),
    supplier_id: Optional[uuid.UUID] = Query(None, description="Filter purchases by supplier"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status: paid, partial, unpaid"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists purchase invoices with pagination, filtering and search."""
    purchases, total_count = list_purchases(
        db=db,
        business_id=current_business.id,
        search=search,
        supplier_id=supplier_id,
        payment_status=payment_status,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=[PurchaseResponse(**p) for p in purchases],
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/{purchase_id}", response_model=ApiResponse[PurchaseResponse])
def get_purchase_detail_endpoint(
    purchase_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns itemized purchase invoice, landed costs breakdown, and payment details."""
    purchase_data = get_purchase_detail(
        db=db,
        business_id=current_business.id,
        purchase_id=purchase_id
    )
    return ApiResponse(data=PurchaseResponse(**purchase_data))
