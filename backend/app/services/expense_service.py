import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
from fastapi import HTTPException, status

from app.models.expense import ExpenseCategory, Expense
from app.schemas.expense import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseOverviewResponse,
    CategoryExpenseBreakdown
)


DEFAULT_CATEGORIES = [
    ("Rent", "Shop, showroom, or godown rental expenses"),
    ("Electricity & Utilities", "EB electricity bills, water, and municipal utility charges"),
    ("Staff Wages", "Staff daily wages, salary advances, overtime, and labor charges"),
    ("Transport & Delivery", "Freight, customer delivery, vehicle fuel, and auto charges"),
    ("Repairs & Maintenance", "Electrical, carpentry, shutter, machine, and shop repairs"),
    ("Packaging", "Polythene carry bags, corrugated boxes, tape, and packing materials"),
    ("Internet & Phone", "Broadband internet, shop telephone, and POS SIM recharges"),
    ("Office Supplies", "Thermal paper rolls, ledger books, bills, and cleaning items"),
    ("Miscellaneous", "Tea, snacks, pooja items, and general operating expenses"),
]


def ensure_default_categories(db: Session, business_id: uuid.UUID) -> None:
    """Auto-seeds standard system default categories if the business has no categories."""
    count = db.execute(
        select(func.count(ExpenseCategory.id)).filter(ExpenseCategory.business_id == business_id)
    ).scalar_one()

    if count == 0:
        for name, desc_text in DEFAULT_CATEGORIES:
            cat = ExpenseCategory(
                id=uuid.uuid4(),
                business_id=business_id,
                name=name,
                description=desc_text,
                is_system_default=True,
                is_active=True
            )
            db.add(cat)
        db.commit()


def get_categories(
    db: Session,
    business_id: uuid.UUID,
    is_active: Optional[bool] = None
) -> List[ExpenseCategory]:
    ensure_default_categories(db, business_id)

    stmt = select(ExpenseCategory).filter(ExpenseCategory.business_id == business_id)
    if is_active is not None:
        stmt = stmt.filter(ExpenseCategory.is_active == is_active)

    stmt = stmt.order_by(desc(ExpenseCategory.is_system_default), ExpenseCategory.name.asc())
    return list(db.execute(stmt).scalars().all())


def create_category(
    db: Session,
    business_id: uuid.UUID,
    data: ExpenseCategoryCreate
) -> ExpenseCategory:
    # Check duplicate name within the business
    existing = db.execute(
        select(ExpenseCategory).filter(
            ExpenseCategory.business_id == business_id,
            func.lower(ExpenseCategory.name) == data.name.strip().lower()
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CATEGORY_ALREADY_EXISTS", "message": "An expense category with this name already exists"}
        )

    cat = ExpenseCategory(
        id=uuid.uuid4(),
        business_id=business_id,
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        is_system_default=False,
        is_active=True
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(
    db: Session,
    business_id: uuid.UUID,
    category_id: uuid.UUID,
    data: ExpenseCategoryUpdate
) -> ExpenseCategory:
    cat = db.execute(
        select(ExpenseCategory).filter(
            ExpenseCategory.id == category_id,
            ExpenseCategory.business_id == business_id
        )
    ).scalar_one_or_none()

    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CATEGORY_NOT_FOUND", "message": "Expense category not found"}
        )

    if data.name is not None and data.name.strip().lower() != cat.name.lower():
        existing = db.execute(
            select(ExpenseCategory).filter(
                ExpenseCategory.business_id == business_id,
                func.lower(ExpenseCategory.name) == data.name.strip().lower(),
                ExpenseCategory.id != category_id
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CATEGORY_ALREADY_EXISTS", "message": "An expense category with this name already exists"}
            )
        cat.name = data.name.strip()

    if data.description is not None:
        cat.description = data.description.strip() if data.description else None

    if data.is_active is not None:
        cat.is_active = data.is_active

    db.commit()
    db.refresh(cat)
    return cat


def delete_category(
    db: Session,
    business_id: uuid.UUID,
    category_id: uuid.UUID
) -> None:
    cat = db.execute(
        select(ExpenseCategory).filter(
            ExpenseCategory.id == category_id,
            ExpenseCategory.business_id == business_id
        )
    ).scalar_one_or_none()

    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CATEGORY_NOT_FOUND", "message": "Expense category not found"}
        )

    # Check if referenced by existing expenses
    expense_count = db.execute(
        select(func.count(Expense.id)).filter(
            Expense.category_id == category_id,
            Expense.business_id == business_id
        )
    ).scalar_one()

    if expense_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CATEGORY_IN_USE", "message": "Cannot delete category referenced by expenses. Deactivate it instead."}
        )

    db.delete(cat)
    db.commit()


def generate_expense_number(db: Session, business_id: uuid.UUID, expense_date: datetime) -> str:
    """Generates unique sequential expense invoice number EXP-YYYYMMDD-XXXX."""
    date_str = expense_date.strftime("%Y%m%d")
    prefix = f"EXP-{date_str}-"

    count = db.execute(
        select(func.count(Expense.id)).filter(
            Expense.business_id == business_id,
            Expense.expense_number.like(f"{prefix}%")
        )
    ).scalar_one()

    return f"{prefix}{count + 1:04d}"


def create_expense(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ExpenseCreate
) -> Expense:
    # 1. Idempotency Check
    if data.idempotency_key:
        existing = db.execute(
            select(Expense).filter(
                Expense.business_id == business_id,
                Expense.idempotency_key == data.idempotency_key
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    # 2. Category Verification
    category = db.execute(
        select(ExpenseCategory).filter(
            ExpenseCategory.id == data.category_id,
            ExpenseCategory.business_id == business_id
        )
    ).scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CATEGORY_NOT_FOUND", "message": "Expense category not found"}
        )
    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CATEGORY_INACTIVE", "message": "Cannot record expense on an inactive category"}
        )

    if data.amount <= Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AMOUNT_MUST_BE_POSITIVE", "message": "Expense amount must be greater than zero"}
        )

    exp_date = data.expense_date or datetime.now(timezone.utc)
    expense_number = generate_expense_number(db, business_id, exp_date)

    expense = Expense(
        id=uuid.uuid4(),
        business_id=business_id,
        category_id=category.id,
        expense_number=expense_number,
        amount=data.amount,
        expense_date=exp_date,
        payment_method=data.payment_method,
        payment_status=data.payment_status,
        payee=data.payee.strip() if data.payee else None,
        description=data.description.strip(),
        reference_number=data.reference_number.strip() if data.reference_number else None,
        idempotency_key=data.idempotency_key.strip() if data.idempotency_key else None,
        created_by_user_id=user_id
    )

    db.add(expense)
    try:
        db.commit()
        db.refresh(expense)
        return expense
    except Exception as e:
        db.rollback()
        raise e


def get_expenses(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[uuid.UUID] = None,
    payment_method: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Expense], int]:
    stmt = select(Expense).filter(Expense.business_id == business_id)

    if start_date:
        stmt = stmt.filter(Expense.expense_date >= start_date)
    if end_date:
        stmt = stmt.filter(Expense.expense_date <= end_date)
    if category_id:
        stmt = stmt.filter(Expense.category_id == category_id)
    if payment_method:
        stmt = stmt.filter(Expense.payment_method == payment_method.lower())
    if payment_status:
        stmt = stmt.filter(Expense.payment_status == payment_status.lower())
    if search:
        search_filter = f"%{search.strip().lower()}%"
        stmt = stmt.filter(
            (func.lower(Expense.expense_number).like(search_filter)) |
            (func.lower(Expense.description).like(search_filter)) |
            (func.lower(Expense.payee).like(search_filter)) |
            (func.lower(Expense.reference_number).like(search_filter))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(desc(Expense.expense_date), desc(Expense.created_at))
    stmt = stmt.offset(offset).limit(limit)

    expenses = list(db.execute(stmt).scalars().all())
    return expenses, total_count


def get_expense(db: Session, business_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
    expense = db.execute(
        select(Expense).filter(
            Expense.id == expense_id,
            Expense.business_id == business_id
        )
    ).scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPENSE_NOT_FOUND", "message": "Expense record not found"}
        )
    return expense


def update_expense(
    db: Session,
    business_id: uuid.UUID,
    expense_id: uuid.UUID,
    data: ExpenseUpdate
) -> Expense:
    expense = get_expense(db, business_id, expense_id)

    if expense.payment_status == "voided":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CANNOT_EDIT_VOIDED_EXPENSE", "message": "Cannot edit a voided expense record"}
        )

    if data.category_id:
        category = db.execute(
            select(ExpenseCategory).filter(
                ExpenseCategory.id == data.category_id,
                ExpenseCategory.business_id == business_id
            )
        ).scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CATEGORY_NOT_FOUND", "message": "Expense category not found"})
        if not category.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "CATEGORY_INACTIVE", "message": "Cannot assign an inactive category"})
        expense.category_id = category.id

    if data.description is not None:
        expense.description = data.description.strip()
    if data.payee is not None:
        expense.payee = data.payee.strip() if data.payee else None
    if data.reference_number is not None:
        expense.reference_number = data.reference_number.strip() if data.reference_number else None
    if data.payment_method is not None:
        valid_modes = {"cash", "upi", "card", "bank_transfer"}
        if data.payment_method.lower() in valid_modes:
            expense.payment_method = data.payment_method.lower()
    if data.expense_date is not None:
        expense.expense_date = data.expense_date

    db.commit()
    db.refresh(expense)
    return expense


def void_expense(
    db: Session,
    business_id: uuid.UUID,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str
) -> Expense:
    expense = get_expense(db, business_id, expense_id)

    if expense.payment_status == "voided":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EXPENSE_ALREADY_VOIDED", "message": "This expense has already been voided"}
        )

    expense.payment_status = "voided"
    expense.voided_at = datetime.now(timezone.utc)
    expense.voided_by_user_id = user_id
    expense.void_reason = reason.strip()

    db.commit()
    db.refresh(expense)
    return expense


def get_expense_overview(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> ExpenseOverviewResponse:
    # Exclude voided expenses from active totals
    base_filter = and_(
        Expense.business_id == business_id,
        Expense.payment_status != "voided"
    )
    if start_date:
        base_filter = and_(base_filter, Expense.expense_date >= start_date)
    if end_date:
        base_filter = and_(base_filter, Expense.expense_date <= end_date)

    # 1. Total Expenses and Count
    total_stmt = select(
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
        func.count(Expense.id)
    ).filter(base_filter)
    total_amount, total_count = db.execute(total_stmt).one()

    # 2. Breakdown by Category
    cat_stmt = select(
        Expense.category_id,
        ExpenseCategory.name,
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000")),
        func.count(Expense.id)
    ).join(ExpenseCategory, Expense.category_id == ExpenseCategory.id).filter(
        base_filter
    ).group_by(
        Expense.category_id, ExpenseCategory.name
    ).order_by(desc(func.sum(Expense.amount)))

    cat_rows = db.execute(cat_stmt).all()
    by_category = [
        CategoryExpenseBreakdown(
            category_id=row[0],
            category_name=row[1],
            total_amount=row[2],
            count=row[3]
        )
        for row in cat_rows
    ]

    # 3. Breakdown by Payment Method
    mode_stmt = select(
        Expense.payment_method,
        func.coalesce(func.sum(Expense.amount), Decimal("0.0000"))
    ).filter(base_filter).group_by(Expense.payment_method)

    mode_rows = db.execute(mode_stmt).all()
    by_payment_method: Dict[str, Decimal] = {row[0]: row[1] for row in mode_rows}

    return ExpenseOverviewResponse(
        total_expenses=total_amount,
        total_count=total_count,
        by_category=by_category,
        by_payment_method=by_payment_method
    )
