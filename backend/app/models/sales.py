import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(GUID, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(GUID, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(GUID, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=False)
    idempotency_key = Column(String(100), nullable=True, index=True)
    status = Column(String(30), default="completed", nullable=False)  # completed, cancelled
    subtotal_amount = Column(Numeric(14, 4), nullable=False)
    discount_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    tax_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    total_amount = Column(Numeric(14, 4), nullable=False)
    paid_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    credit_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)  # total - paid
    cogs_total = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    payment_method = Column(String(50), nullable=False)  # cash, upi, card, credit, split
    payment_status = Column(String(30), nullable=False)  # paid, partial, unpaid
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("business_id", "invoice_number", name="uq_sales_business_invoice_number"),
        UniqueConstraint("business_id", "idempotency_key", name="uq_sales_business_idempotency_key"),
    )

    # Relationships
    business = relationship("Business")
    branch = relationship("Branch")
    warehouse = relationship("Warehouse")
    customer = relationship("Customer", back_populates="sales")
    created_by_user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan", order_by="SaleItem.id")
    payments = relationship("Payment", back_populates="sale", cascade="all, delete-orphan", order_by="Payment.created_at")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    sale_id = Column(GUID, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit_price = Column(Numeric(14, 4), nullable=False)
    discount_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    total_price = Column(Numeric(14, 4), nullable=False)  # (quantity * unit_price) - discount
    unit_cost = Column(Numeric(14, 4), nullable=False)  # Moving average cost at the moment of sale
    line_cogs = Column(Numeric(14, 4), nullable=False)  # quantity * unit_cost

    # Relationships
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    sale_id = Column(GUID, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(GUID, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    purchase_id = Column(GUID, ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(GUID, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_direction = Column(String(20), default="inflow", nullable=False)  # inflow, outflow
    payment_mode = Column(String(30), nullable=False)  # cash, upi, card, bank_transfer
    amount = Column(Numeric(14, 4), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    business = relationship("Business")
    sale = relationship("Sale", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    purchase = relationship("Purchase", back_populates="payments")
    supplier = relationship("Supplier", back_populates="payments")
    created_by_user = relationship("User")
