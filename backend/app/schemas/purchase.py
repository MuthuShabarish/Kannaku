import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PurchaseItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=Decimal("0.0000"), description="Quantity received")
    unit_cost: Decimal = Field(..., ge=Decimal("0.0000"), description="Purchase price per unit before line discount")
    discount_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"), description="Line-level discount")


class PurchaseSplitPaymentItem(BaseModel):
    mode: str = Field(..., description="cash, upi, card, or bank_transfer")
    amount: Decimal = Field(..., gt=Decimal("0.0000"))


class PurchaseCreate(BaseModel):
    supplier_id: Optional[uuid.UUID] = Field(None, description="Optional supplier UUID")
    supplier_invoice_ref: Optional[str] = Field(None, max_length=100, description="Supplier's bill/invoice number")
    idempotency_key: Optional[str] = Field(None, max_length=100, description="Client idempotency key")
    purchase_date: Optional[datetime] = Field(None, description="Purchase date/time")
    items: List[PurchaseItemCreate] = Field(..., min_length=1, description="List of purchased products")
    discount_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"), description="Overall bill discount")
    payment_method: str = Field(default="cash", description="cash, upi, card, bank_transfer, credit, or split")
    paid_amount: Optional[Decimal] = Field(None, ge=Decimal("0.0000"), description="Amount paid immediately")
    split_payments: Optional[List[PurchaseSplitPaymentItem]] = Field(None, description="Breakdown for split payment")
    notes: Optional[str] = Field(None, description="Notes on the purchase")


class PurchaseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: Optional[str] = None
    unit: str
    quantity: Decimal
    unit_cost: Decimal
    discount_amount: Decimal
    total_cost: Decimal
    effective_unit_cost: Decimal


class PurchasePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_mode: str
    amount: Decimal
    notes: Optional[str] = None
    created_at: datetime


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    invoice_number: str
    supplier_invoice_ref: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    supplier_phone: Optional[str] = None
    status: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    credit_amount: Decimal
    payment_method: str
    payment_status: str
    purchase_date: datetime
    notes: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_by_user_name: Optional[str] = None
    created_at: datetime
    items: List[PurchaseItemResponse] = []
    payments: List[PurchasePaymentResponse] = []


class PurchaseListResponse(BaseModel):
    items: List[PurchaseResponse]
    total: int
    limit: int
    offset: int


class PurchaseOverviewResponse(BaseModel):
    total_purchases_count: int
    total_purchases_amount: Decimal
    total_paid_amount: Decimal
    total_credit_amount: Decimal
    total_suppliers: int
    total_payable: Decimal
