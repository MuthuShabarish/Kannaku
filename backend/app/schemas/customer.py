import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=7, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=1000)
    credit_limit: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))

    @field_validator("name")
    def name_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Customer name cannot be empty")
        return s

    @field_validator("phone")
    def phone_cleanup(cls, v: str) -> str:
        s = v.strip().replace(" ", "").replace("-", "")
        if len(s) < 7:
            raise ValueError("Phone number must have at least 7 digits")
        return s


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=1000)
    credit_limit: Optional[Decimal] = Field(None, ge=Decimal("0.0000"))
    is_active: Optional[bool] = None

    @field_validator("name")
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Customer name cannot be empty")
            return s
        return v

    @field_validator("phone")
    def phone_cleanup(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip().replace(" ", "").replace("-", "")
            if len(s) < 7:
                raise ValueError("Phone number must have at least 7 digits")
            return s
        return v


class CustomerPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.0000"))
    payment_mode: str = Field("cash", pattern="^(cash|upi|card|bank_transfer)$")
    notes: Optional[str] = Field(None, max_length=500)


class CustomerLedgerEntryResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    customer_id: uuid.UUID
    entry_type: str
    reference_id: Optional[uuid.UUID] = None
    amount: Decimal
    balance_after: Decimal
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Decimal
    current_balance: Decimal
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerDetailResponse(CustomerResponse):
    recent_entries: List[CustomerLedgerEntryResponse] = []
