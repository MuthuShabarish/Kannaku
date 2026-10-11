import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerDetailResponse,
    CustomerPaymentCreate,
    CustomerLedgerEntryResponse
)
from app.services.customer_service import (
    create_customer,
    list_customers,
    get_customer_detail,
    update_customer,
    record_customer_payment
)

router = APIRouter(prefix="/api/v1/customers", tags=["Customers & Khata Ledger"])


@router.post("", response_model=ApiResponse[CustomerResponse], status_code=status.HTTP_201_CREATED)
def create_customer_endpoint(
    req: CustomerCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new customer for Khata ledger tracking and sales association."""
    customer = create_customer(db=db, business_id=current_business.id, req=req)
    return ApiResponse(
        data=CustomerResponse.model_validate(customer),
        message="Customer created successfully"
    )


@router.get("", response_model=ApiResponse[List[CustomerResponse]])
def list_customers_endpoint(
    search: Optional[str] = Query(None, description="Search by name, phone or email"),
    with_balance_only: Optional[bool] = Query(None, description="Filter customers with outstanding debt only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists customers scoped to the authorized tenant business."""
    customers, total_count = list_customers(
        db=db,
        business_id=current_business.id,
        search=search,
        with_balance_only=with_balance_only,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=[CustomerResponse.model_validate(c) for c in customers],
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/{customer_id}", response_model=ApiResponse[CustomerDetailResponse])
def get_customer_detail_endpoint(
    customer_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches customer profile and Khata ledger transaction entries."""
    detail = get_customer_detail(db=db, business_id=current_business.id, customer_id=customer_id)
    return ApiResponse(data=CustomerDetailResponse(**detail))


@router.put("/{customer_id}", response_model=ApiResponse[CustomerResponse])
def update_customer_endpoint(
    customer_id: uuid.UUID,
    req: CustomerUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates customer details, credit limit, or active status."""
    customer = update_customer(
        db=db,
        business_id=current_business.id,
        customer_id=customer_id,
        req=req
    )
    return ApiResponse(
        data=CustomerResponse.model_validate(customer),
        message="Customer updated successfully"
    )


@router.post("/{customer_id}/payments", response_model=ApiResponse[CustomerLedgerEntryResponse], status_code=status.HTTP_201_CREATED)
def record_customer_payment_endpoint(
    customer_id: uuid.UUID,
    req: CustomerPaymentCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records a payment against customer's outstanding balance (Khata settlement).
    Pessimistic locking prevents double counting.
    """
    customer, entry = record_customer_payment(
        db=db,
        business_id=current_business.id,
        customer_id=customer_id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=CustomerLedgerEntryResponse.model_validate(entry),
        message=f"Payment of {entry.amount} recorded. Updated balance: {customer.current_balance}."
    )
