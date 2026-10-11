import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseVoid,
    ExpenseResponse,
    ExpenseOverviewResponse
)
from app.services.expense_service import (
    create_expense,
    get_expenses,
    get_expense,
    update_expense,
    void_expense,
    get_expense_overview
)

router = APIRouter(prefix="/api/v1/expenses", tags=["Operating Expenses"])


@router.post("", response_model=ApiResponse[ExpenseResponse], status_code=status.HTTP_201_CREATED)
def create_expense_endpoint(
    req: ExpenseCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records an operating expense atomically with tenant isolation."""
    expense = create_expense(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        data=req
    )
    res = ExpenseResponse.model_validate(expense)
    if expense.category:
        res.category_name = expense.category.name

    return ApiResponse(
        data=res,
        message="Expense recorded successfully"
    )


@router.get("", response_model=ApiResponse[List[ExpenseResponse]])
def list_expenses_endpoint(
    start_date: Optional[datetime] = Query(None, description="Filter from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    payment_method: Optional[str] = Query(None, description="cash, upi, card, or bank_transfer"),
    payment_status: Optional[str] = Query(None, description="paid, unpaid, or voided"),
    search: Optional[str] = Query(None, description="Search description, payee, or reference"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists expenses with multi-field filtering and pagination."""
    expenses, total_count = get_expenses(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        payment_method=payment_method,
        payment_status=payment_status,
        search=search,
        limit=limit,
        offset=offset
    )

    data = []
    for exp in expenses:
        item = ExpenseResponse.model_validate(exp)
        if exp.category:
            item.category_name = exp.category.name
        data.append(item)

    return ApiResponse(
        data=data,
        meta={"total": total_count, "limit": limit, "offset": offset}
    )


@router.get("/overview", response_model=ApiResponse[ExpenseOverviewResponse])
def get_expense_overview_endpoint(
    start_date: Optional[datetime] = Query(None, description="Filter from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date"),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves aggregated operating expense metrics and category distributions."""
    overview = get_expense_overview(
        db=db,
        business_id=current_business.id,
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse(data=overview)


@router.get("/{expense_id}", response_model=ApiResponse[ExpenseResponse])
def get_expense_endpoint(
    expense_id: uuid.UUID,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full details of a specific expense."""
    expense = get_expense(
        db=db,
        business_id=current_business.id,
        expense_id=expense_id
    )
    res = ExpenseResponse.model_validate(expense)
    if expense.category:
        res.category_name = expense.category.name
    return ApiResponse(data=res)


@router.put("/{expense_id}", response_model=ApiResponse[ExpenseResponse])
def update_expense_endpoint(
    expense_id: uuid.UUID,
    req: ExpenseUpdate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates non-financial metadata on an active expense."""
    expense = update_expense(
        db=db,
        business_id=current_business.id,
        expense_id=expense_id,
        data=req
    )
    res = ExpenseResponse.model_validate(expense)
    if expense.category:
        res.category_name = expense.category.name
    return ApiResponse(data=res, message="Expense updated successfully")


@router.post("/{expense_id}/void", response_model=ApiResponse[ExpenseResponse])
def void_expense_endpoint(
    expense_id: uuid.UUID,
    req: ExpenseVoid,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Voids an expense, removing it from active totals while preserving an audit trail."""
    expense = void_expense(
        db=db,
        business_id=current_business.id,
        expense_id=expense_id,
        user_id=current_user.id,
        reason=req.reason
    )
    res = ExpenseResponse.model_validate(expense)
    if expense.category:
        res.category_name = expense.category.name
    return ApiResponse(data=res, message="Expense voided successfully")
