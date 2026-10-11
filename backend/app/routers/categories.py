import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inventory import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse
)
from app.services.inventory_service import (
    create_category,
    list_categories,
    update_category,
    delete_category
)

router = APIRouter(prefix="/api/v1/categories", tags=["Product Categories"])


@router.get("", response_model=ApiResponse[List[CategoryResponse]])
def get_categories(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all product categories with associated active product counts for tenant."""
    records = list_categories(db, current_business.id)
    data = []
    for cat, prod_count in records:
        data.append(
            CategoryResponse(
                id=cat.id,
                business_id=cat.business_id,
                name=cat.name,
                tamil_name=cat.tamil_name,
                display_order=cat.display_order,
                is_active=cat.is_active,
                product_count=prod_count or 0,
                created_at=cat.created_at
            )
        )
    return ApiResponse(data=data)


@router.post("", response_model=ApiResponse[CategoryResponse], status_code=status.HTTP_201_CREATED)
def add_category(
    req: CategoryCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new product category for tenant with uniqueness verification."""
    cat = create_category(db, current_business.id, req)
    return ApiResponse(
        data=CategoryResponse(
            id=cat.id,
            business_id=cat.business_id,
            name=cat.name,
            tamil_name=cat.tamil_name,
            display_order=cat.display_order,
            is_active=cat.is_active,
            product_count=0,
            created_at=cat.created_at
        )
    )


@router.put("/{category_id}", response_model=ApiResponse[CategoryResponse])
def edit_category(
    category_id: uuid.UUID,
    req: CategoryUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an existing category for tenant."""
    cat = update_category(db, current_business.id, category_id, req)
    return ApiResponse(
        data=CategoryResponse(
            id=cat.id,
            business_id=cat.business_id,
            name=cat.name,
            tamil_name=cat.tamil_name,
            display_order=cat.display_order,
            is_active=cat.is_active,
            product_count=0,
            created_at=cat.created_at
        )
    )


@router.delete("/{category_id}", response_model=ApiResponse[dict])
def remove_category(
    category_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a category and unassigns linked products."""
    delete_category(db, current_business.id, category_id)
    return ApiResponse(data={"message": "Category deleted successfully"})
