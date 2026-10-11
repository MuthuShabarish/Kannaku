import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    credit_limit = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    current_balance = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)  # Positive = Receivable (customer owes shop)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "phone", name="uq_customers_business_phone"),
    )

    # Relationships
    business = relationship("Business")
    sales = relationship("Sale", back_populates="customer")
    ledger_entries = relationship("CustomerLedgerEntry", back_populates="customer", cascade="all, delete-orphan", order_by="CustomerLedgerEntry.created_at.desc()")
    payments = relationship("Payment", back_populates="customer")


class CustomerLedgerEntry(Base):
    __tablename__ = "customer_ledger_entries"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(GUID, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String(50), nullable=False)  # 'credit_sale', 'payment_received', 'balance_adjustment'
    reference_id = Column(GUID, nullable=True, index=True)  # sale_id or payment_id
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
    customer = relationship("Customer", back_populates="ledger_entries")
    created_by_user = relationship("User")
