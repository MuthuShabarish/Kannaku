import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class Purchase(Base, TimestampMixin):
    __tablename__ = "purchases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(GUID, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(GUID, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(GUID, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=False)
    supplier_invoice_ref = Column(String(100), nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    status = Column(String(30), default="received", nullable=False)  # received, cancelled
    subtotal_amount = Column(Numeric(14, 4), nullable=False)
    discount_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    tax_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    total_amount = Column(Numeric(14, 4), nullable=False)
    paid_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    credit_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)  # total - paid (accounts payable)
    payment_method = Column(String(50), nullable=False)  # cash, upi, card, bank_transfer, credit, split
    payment_status = Column(String(30), nullable=False)  # paid, partial, unpaid
    purchase_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("business_id", "invoice_number", name="uq_purchases_business_invoice_number"),
        UniqueConstraint("business_id", "idempotency_key", name="uq_purchases_business_idempotency_key"),
    )

    # Relationships
    business = relationship("Business")
    branch = relationship("Branch")
    warehouse = relationship("Warehouse")
    supplier = relationship("Supplier", back_populates="purchases")
    created_by_user = relationship("User")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan", order_by="PurchaseItem.id")
    payments = relationship("Payment", back_populates="purchase", cascade="all, delete-orphan", order_by="Payment.created_at")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    purchase_id = Column(GUID, ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit_cost = Column(Numeric(14, 4), nullable=False)  # Nominal purchase price per unit
    discount_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)  # Line discount
    total_cost = Column(Numeric(14, 4), nullable=False)  # (quantity * unit_cost) - discount_amount
    effective_unit_cost = Column(Numeric(14, 4), nullable=False)  # Landed unit cost after proportional invoice discount

    # Relationships
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")
