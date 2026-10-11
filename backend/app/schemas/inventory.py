import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tamil_name: Optional[str] = Field(None, max_length=255)
    display_order: int = Field(0, ge=0)

    @field_validator("name")
    def name_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Category name cannot be empty")
        return s


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tamil_name: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("name")
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Category name cannot be empty")
            return s
        return v


class CategoryResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    tamil_name: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    product_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tamil_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category_id: Optional[uuid.UUID] = None
    sku: Optional[str] = Field(None, max_length=100)
    unit: str = Field("piece", min_length=1, max_length=50)
    purchase_cost: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    selling_price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    low_stock_threshold: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_active: bool = True
    opening_stock: Optional[Decimal] = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    opening_stock_cost: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))

    @field_validator("name")
    def name_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Product name cannot be empty")
        return s

    @field_validator("sku")
    def sku_cleanup(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            return s if s else None
        return None

    @field_validator("unit")
    def unit_cleanup(cls, v: str) -> str:
        s = v.strip().lower()
        if not s:
            return "piece"
        return s


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tamil_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category_id: Optional[uuid.UUID] = None
    sku: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    purchase_cost: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    selling_price: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    low_stock_threshold: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    is_active: Optional[bool] = None

    @field_validator("name")
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Product name cannot be empty")
            return s
        return v

    @field_validator("sku")
    def sku_cleanup(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            return s if s else None
        return None


class ProductStatusUpdate(BaseModel):
    is_active: bool


class ProductResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    name: str
    tamil_name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    unit: str
    purchase_cost: Decimal
    selling_price: Decimal
    low_stock_threshold: Decimal
    current_stock: Decimal = Decimal("0.00")
    stock_status: str = "in_stock"  # "in_stock", "low_stock", "out_of_stock"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockAdjustmentCreate(BaseModel):
    product_id: uuid.UUID
    adjustment_type: str = Field(..., pattern="^(increase|decrease)$")
    quantity: Decimal = Field(..., gt=Decimal("0.00"))
    reason: str = Field(..., min_length=3, max_length=500)
    unit_cost: Optional[Decimal] = Field(None, ge=Decimal("0.00"))

    @field_validator("reason")
    def reason_not_empty(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3:
            raise ValueError("Reason must be at least 3 characters explaining the stock adjustment")
        return s


class StockMovementResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    movement_type: str
    quantity_delta: Decimal
    balance_after: Decimal
    unit_cost: Decimal
    reason: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_by_user_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    recent_movements: List[StockMovementResponse] = []


class InventoryOverviewResponse(BaseModel):
    total_products: int
    active_products: int
    low_stock_products: int
    out_of_stock_products: int
    total_stock_value: Decimal
    total_categories: int
