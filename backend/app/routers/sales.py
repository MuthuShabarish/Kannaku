import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.sales import (
    SaleCreate,
    SaleResponse,
    SalesOverviewResponse
)
from app.services.sales_service import (
    create_sale,
    get_sale_detail,
    list_sales,
    get_sales_overview
)

router = APIRouter(prefix="/api/v1/sales", tags=["Sales Billing & POS Checkout"])


@router.post("", response_model=ApiResponse[SaleResponse], status_code=status.HTTP_201_CREATED)
def checkout_sale_endpoint(
    req: SaleCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a Point-of-Sale (POS) atomic checkout:
    - Deducts inventory with pessimistic locking (safe against overselling).
    - Captures Moving Average Cost (MAC) snapshot for COGS.
    - Idempotency control via idempotency_key prevents duplicate billing.
    - Updates Customer Khata balance if credit or partial payment is made.
    """
    sale_data = create_sale(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=SaleResponse(**sale_data),
        message=f"Sale completed successfully. Invoice: {sale_data['invoice_number']}."
    )


@router.get("/overview", response_model=ApiResponse[SalesOverviewResponse])
def get_sales_overview_endpoint(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns aggregated sales revenue, credit total, COGS, and customer receivables."""
    metrics = get_sales_overview(db=db, business_id=current_business.id)
    return ApiResponse(data=SalesOverviewResponse(**metrics))


@router.get("", response_model=ApiResponse[List[SaleResponse]])
def list_sales_endpoint(
    search: Optional[str] = Query(None, description="Search by invoice number, customer name or phone"),
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter sales by customer"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status: paid, partial, unpaid"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists sales invoices with pagination, filtering and search."""
    sales, total_count = list_sales(
        db=db,
        business_id=current_business.id,
        search=search,
        customer_id=customer_id,
        payment_status=payment_status,
        limit=limit,
        offset=offset
    )
    return ApiResponse(
        data=[SaleResponse(**s) for s in sales],
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/{sale_id}", response_model=ApiResponse[SaleResponse])
def get_sale_detail_endpoint(
    sale_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns completed sale itemized receipt, pricing breakdown, and payment details."""
    sale_data = get_sale_detail(
        db=db,
        business_id=current_business.id,
        sale_id=sale_id
    )
    return ApiResponse(data=SaleResponse(**sale_data))
