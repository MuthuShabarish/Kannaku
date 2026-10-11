import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class ExpenseCategory(Base, TimestampMixin):
    __tablename__ = "expense_categories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "name", name="uq_expense_category_business_name"),
    )

    # Relationships
    business = relationship("Business")
    expenses = relationship("Expense", back_populates="category")


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(GUID, ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    expense_number = Column(String(100), nullable=False, index=True)  # EXP-YYYYMMDD-XXXX
    amount = Column(Numeric(14, 4), nullable=False)
    expense_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    payment_method = Column(String(30), default="cash", nullable=False)  # cash, upi, card, bank_transfer
    payment_status = Column(String(20), default="paid", nullable=False, index=True)  # paid, unpaid, voided
    payee = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    reference_number = Column(String(100), nullable=True)  # Receipt / Bill / UTR reference
    idempotency_key = Column(String(100), nullable=True, index=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    void_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("business_id", "expense_number", name="uq_expense_business_number"),
        UniqueConstraint("business_id", "idempotency_key", name="uq_expense_business_idempotency"),
    )

    # Relationships
    business = relationship("Business")
    category = relationship("ExpenseCategory", back_populates="expenses")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    voided_by_user = relationship("User", foreign_keys=[voided_by_user_id])
