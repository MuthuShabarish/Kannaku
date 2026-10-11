import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category name, e.g. Rent, Electricity")
    description: Optional[str] = Field(None, description="Optional description of expense purpose")


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_system_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExpenseCreate(BaseModel):
    category_id: uuid.UUID = Field(..., description="Target expense category ID")
    amount: Decimal = Field(..., gt=Decimal("0.0000"), description="Positive expense amount")
    expense_date: Optional[datetime] = Field(None, description="Transaction date/time (defaults to current time)")
    payment_method: str = Field("cash", description="cash, upi, card, or bank_transfer")
    payment_status: str = Field("paid", description="paid or unpaid")
    payee: Optional[str] = Field(None, max_length=255, description="Payee / vendor / recipient name")
    description: str = Field(..., min_length=1, description="Purpose or explanation of operating expense")
    reference_number: Optional[str] = Field(None, max_length=100, description="Receipt / bill / voucher / UTR reference")
    idempotency_key: Optional[str] = Field(None, max_length=100, description="Idempotency key to prevent double posting")

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid_modes = {"cash", "upi", "card", "bank_transfer"}
        if v.lower() not in valid_modes:
            raise ValueError(f"Invalid payment method '{v}'. Must be one of: {', '.join(valid_modes)}")
        return v.lower()

    @field_validator("payment_status")
    @classmethod
    def validate_payment_status(cls, v: str) -> str:
        valid_statuses = {"paid", "unpaid"}
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid payment status '{v}'. Initial status must be 'paid' or 'unpaid'")
        return v.lower()


class ExpenseUpdate(BaseModel):
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(None, min_length=1)
    payee: Optional[str] = None
    reference_number: Optional[str] = None
    payment_method: Optional[str] = None
    expense_date: Optional[datetime] = None


class ExpenseVoid(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Audit reason for voiding this expense")


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    category_id: uuid.UUID
    category_name: Optional[str] = None
    expense_number: str
    amount: Decimal
    expense_date: datetime
    payment_method: str
    payment_status: str
    payee: Optional[str] = None
    description: str
    reference_number: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CategoryExpenseBreakdown(BaseModel):
    category_id: uuid.UUID
    category_name: str
    total_amount: Decimal
    count: int


class ExpenseOverviewResponse(BaseModel):
    total_expenses: Decimal
    total_count: int
    by_category: List[CategoryExpenseBreakdown]
    by_payment_method: Dict[str, Decimal]
