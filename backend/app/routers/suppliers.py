import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierDetailResponse,
    SupplierPaymentCreate,
    SupplierLedgerEntryResponse
)
from app.services.supplier_service import (
    create_supplier,
    list_suppliers,
    get_supplier_detail,
    update_supplier,
    record_supplier_payment,
    get_supplier_ledger
)

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers & Accounts Payable"])


@router.post("", response_model=ApiResponse[SupplierResponse], status_code=status.HTTP_201_CREATED)
def create_supplier_endpoint(
    req: SupplierCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new supplier for purchase tracking and accounts payable ledger."""
    supplier = create_supplier(db=db, business_id=current_business.id, req=req)
    return ApiResponse(
        data=SupplierResponse.model_validate(supplier),
        message="Supplier created successfully"
    )


@router.get("", response_model=ApiResponse[List[SupplierResponse]])
def list_suppliers_endpoint(
    search: Optional[str] = Query(None, description="Search by name, phone or email"),
    with_balance_only: Optional[bool] = Query(None, description="Filter suppliers with outstanding payables only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists suppliers scoped to the authorized tenant business."""
    suppliers, total_count = list_suppliers(
        db=db,
        business_id=current_business.id,
        search=search,
        with_balance_only=with_balance_only,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=[SupplierResponse.model_validate(s) for s in suppliers],
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/{supplier_id}", response_model=ApiResponse[SupplierDetailResponse])
def get_supplier_detail_endpoint(
    supplier_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches supplier profile and recent accounts payable ledger transactions."""
    detail = get_supplier_detail(db=db, business_id=current_business.id, supplier_id=supplier_id)
    return ApiResponse(data=SupplierDetailResponse(**detail))


@router.put("/{supplier_id}", response_model=ApiResponse[SupplierResponse])
def update_supplier_endpoint(
    supplier_id: uuid.UUID,
    req: SupplierUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates supplier details, notes, or active status."""
    supplier = update_supplier(
        db=db,
        business_id=current_business.id,
        supplier_id=supplier_id,
        req=req
    )
    return ApiResponse(
        data=SupplierResponse.model_validate(supplier),
        message="Supplier updated successfully"
    )


@router.post("/{supplier_id}/payments", response_model=ApiResponse[SupplierLedgerEntryResponse], status_code=status.HTTP_201_CREATED)
def record_supplier_payment_endpoint(
    supplier_id: uuid.UUID,
    req: SupplierPaymentCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records a payment made against a supplier's outstanding balance (AP settlement).
    Pessimistic locking prevents double counting and oversettlement.
    """
    supplier, entry = record_supplier_payment(
        db=db,
        business_id=current_business.id,
        supplier_id=supplier_id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=SupplierLedgerEntryResponse.model_validate(entry),
        message=f"Payment of {entry.amount} recorded. Updated balance: {supplier.current_balance}."
    )


@router.get("/{supplier_id}/ledger", response_model=ApiResponse[List[SupplierLedgerEntryResponse]])
def get_supplier_ledger_endpoint(
    supplier_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists paginated ledger history for a specific supplier."""
    entries, total_count = get_supplier_ledger(
        db=db,
        business_id=current_business.id,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=[SupplierLedgerEntryResponse.model_validate(e) for e in entries],
        meta={"total": total_count, "limit": limit, "offset": offset}
    )
