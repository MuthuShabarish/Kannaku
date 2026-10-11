import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, Numeric, ForeignKey, Text, UniqueConstraint, CheckConstraint, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    tamil_name = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "name", name="uq_categories_business_name"),
    )

    # Relationships
    business = relationship("Business")
    products = relationship("Product", back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    tamil_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    sku = Column(String(100), nullable=True, index=True)
    unit = Column(String(50), default="piece", nullable=False)  # piece, kg, gram, litre, box, dozen
    purchase_cost = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    selling_price = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    low_stock_threshold = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
    )

    # Relationships
    business = relationship("Business")
    category = relationship("Category", back_populates="products")
    inventory_balances = relationship("InventoryBalance", back_populates="product", cascade="all, delete-orphan")
    movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")


class InventoryBalance(Base, TimestampMixin):
    __tablename__ = "inventory_balances"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(GUID, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    current_stock = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    reserved_stock = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    average_cost = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)

    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_balance_warehouse_product"),
        CheckConstraint("current_stock >= 0", name="chk_current_stock_non_negative"),
    )

    # Relationships
    business = relationship("Business")
    warehouse = relationship("Warehouse")
    product = relationship("Product", back_populates="inventory_balances")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(GUID, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False)  # 'opening', 'adjustment_increase', 'adjustment_decrease'
    quantity_delta = Column(Numeric(14, 4), nullable=False)
    balance_after = Column(Numeric(14, 4), nullable=False)
    unit_cost = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    reason = Column(Text, nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    business = relationship("Business")
    warehouse = relationship("Warehouse")
    product = relationship("Product", back_populates="movements")
    created_by_user = relationship("User")
