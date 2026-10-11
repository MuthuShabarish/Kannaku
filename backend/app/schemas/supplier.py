import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Supplier or vendor name")
    phone: Optional[str] = Field(None, max_length=20, description="Optional phone number")
    email: Optional[str] = Field(None, max_length=255, description="Optional email address")
    address: Optional[str] = Field(None, description="Optional street / city address")
    notes: Optional[str] = Field(None, description="Optional notes or terms")


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.0000"), description="Payment settlement amount")
    payment_mode: str = Field("cash", description="cash, upi, card, or bank_transfer")
    notes: Optional[str] = Field(None, description="Optional reference or transaction note")


class SupplierLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    entry_type: str
    reference_id: Optional[uuid.UUID] = None
    amount: Decimal
    balance_after: Decimal
    notes: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    current_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierDetailResponse(SupplierResponse):
    recent_entries: List[SupplierLedgerEntryResponse] = []


class SupplierListResponse(BaseModel):
    items: List[SupplierResponse]
    total: int
    limit: int
    offset: int
