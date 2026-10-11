import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.expense import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCategoryResponse
)
from app.services.expense_service import (
    get_categories,
    create_category,
    update_category,
    delete_category
)

router = APIRouter(prefix="/api/v1/expense-categories", tags=["Expense Categories"])


@router.get("", response_model=ApiResponse[List[ExpenseCategoryResponse]])
def list_categories_endpoint(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists expense categories for the authorized tenant, auto-seeding defaults if none exist."""
    categories = get_categories(
        db=db,
        business_id=current_business.id,
        is_active=is_active
    )
    return ApiResponse(
        data=[ExpenseCategoryResponse.model_validate(c) for c in categories]
    )


@router.post("", response_model=ApiResponse[ExpenseCategoryResponse], status_code=status.HTTP_201_CREATED)
def create_category_endpoint(
    req: ExpenseCategoryCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a custom expense category for the business."""
    category = create_category(
        db=db,
        business_id=current_business.id,
        data=req
    )
    return ApiResponse(
        data=ExpenseCategoryResponse.model_validate(category),
        message="Category created successfully"
    )


@router.put("/{category_id}", response_model=ApiResponse[ExpenseCategoryResponse])
def update_category_endpoint(
    category_id: uuid.UUID,
    req: ExpenseCategoryUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates a category's name, description, or active status."""
    category = update_category(
        db=db,
        business_id=current_business.id,
        category_id=category_id,
        data=req
    )
    return ApiResponse(
        data=ExpenseCategoryResponse.model_validate(category),
        message="Category updated successfully"
    )


@router.delete("/{category_id}", response_model=ApiResponse[None])
def delete_category_endpoint(
    category_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an unused category. Rejects deletion if referenced by existing expenses."""
    delete_category(
        db=db,
        business_id=current_business.id,
        category_id=category_id
    )
    return ApiResponse(
        data=None,
        message="Category deleted successfully"
    )
