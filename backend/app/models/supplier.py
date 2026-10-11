import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    current_balance = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)  # Positive = Accounts Payable (owed to supplier)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    business = relationship("Business")
    purchases = relationship("Purchase", back_populates="supplier")
    ledger_entries = relationship("SupplierLedgerEntry", back_populates="supplier", cascade="all, delete-orphan", order_by="SupplierLedgerEntry.created_at.desc()")
    payments = relationship("Payment", back_populates="supplier")


class SupplierLedgerEntry(Base):
    __tablename__ = "supplier_ledger_entries"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(GUID, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String(50), nullable=False)  # 'credit_purchase', 'payment_made', 'balance_adjustment'
    reference_id = Column(GUID, nullable=True, index=True)  # purchase_id or payment_id
    amount = Column(Numeric(14, 4), nullable=False)
    balance_after = Column(Numeric(14, 4), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="ledger_entries")
    created_by_user = relationship("User")
