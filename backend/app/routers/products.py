import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inventory import (
    ProductCreate,
    ProductUpdate,
    ProductStatusUpdate,
    ProductResponse,
    ProductDetailResponse
)
from app.services.inventory_service import (
    create_product,
    update_product,
    toggle_product_status,
    list_products,
    get_product_detail
)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("", response_model=ApiResponse[List[ProductResponse]])
def get_products(
    search: Optional[str] = Query(None, description="Search term for product name, SKU, or description"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    low_stock: Optional[bool] = Query(None, description="Filter only low stock products"),
    sort_by: str = Query("created_at", description="Sort field: created_at, name, selling_price, current_stock"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves filtered and paginated product list for tenant with real-time stock balances.
    """
    results, total_count = list_products(
        db=db,
        business_id=current_business.id,
        search=search,
        category_id=category_id,
        is_active=is_active,
        low_stock=low_stock,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset
    )
    return ApiResponse(data=[ProductResponse(**item) for item in results])


@router.post("", response_model=ApiResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
def add_product(
    req: ProductCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new product with optional initial opening stock and movement traceability.
    """
    product, opening_qty = create_product(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        req=req
    )
    detail = get_product_detail(db, current_business.id, product.id)
    return ApiResponse(data=ProductResponse(**detail))


@router.get("/{product_id}", response_model=ApiResponse[ProductDetailResponse])
def get_product(
    product_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves complete product specification and traceable stock movement history.
    """
    detail = get_product_detail(db, current_business.id, product_id)
    return ApiResponse(data=ProductDetailResponse(**detail))


@router.put("/{product_id}", response_model=ApiResponse[ProductResponse])
def edit_product(
    product_id: uuid.UUID,
    req: ProductUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates core product metadata. Cannot directly overwrite stock balances.
    """
    update_product(
        db=db,
        business_id=current_business.id,
        product_id=product_id,
        req=req
    )
    detail = get_product_detail(db, current_business.id, product_id)
    return ApiResponse(data=ProductResponse(**detail))


@router.patch("/{product_id}/status", response_model=ApiResponse[ProductResponse])
def set_product_status(
    product_id: uuid.UUID,
    req: ProductStatusUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggles product active / inactive lifecycle status.
    """
    toggle_product_status(
        db=db,
        business_id=current_business.id,
        product_id=product_id,
        is_active=req.is_active
    )
    detail = get_product_detail(db, current_business.id, product_id)
    return ApiResponse(data=ProductResponse(**detail))
