import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=Decimal("0.0000"))
    discount_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))


class SplitPaymentItem(BaseModel):
    mode: str = Field(..., pattern="^(cash|upi|card|bank_transfer)$")
    amount: Decimal = Field(..., gt=Decimal("0.0000"))


class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(..., min_length=1)
    customer_id: Optional[uuid.UUID] = None
    discount_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    payment_method: str = Field("cash", pattern="^(cash|upi|card|credit|split)$")
    paid_amount: Optional[Decimal] = Field(None, ge=Decimal("0.0000"))
    split_payments: Optional[List[SplitPaymentItem]] = None
    notes: Optional[str] = Field(None, max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=100)

    @field_validator("idempotency_key")
    def clean_idempotency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            return s if s else None
        return None


class SaleItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: Optional[str] = None
    unit: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    total_price: Decimal
    unit_cost: Decimal
    line_cogs: Decimal

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    id: uuid.UUID
    payment_mode: str
    amount: Decimal
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    invoice_number: str
    customer_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    credit_amount: Decimal
    cogs_total: Decimal
    payment_method: str
    payment_status: str
    notes: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_by_user_name: Optional[str] = None
    created_at: datetime
    items: List[SaleItemResponse] = []
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True


class SalesOverviewResponse(BaseModel):
    total_sales_count: int
    total_sales_amount: Decimal
    total_paid_amount: Decimal
    total_credit_amount: Decimal
    total_cogs: Decimal
    total_customers: int
    total_receivable: Decimal
