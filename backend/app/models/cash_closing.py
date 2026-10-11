import uuid
from decimal import Decimal
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Numeric, ForeignKey, Text, UniqueConstraint, DateTime, Date
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin


class DailyCashClosing(Base, TimestampMixin):
    __tablename__ = "daily_cash_closings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(GUID, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True)
    closing_date = Column(Date, nullable=False, index=True)
    session_start = Column(DateTime(timezone=True), nullable=False)
    session_end = Column(DateTime(timezone=True), nullable=False)
    opening_cash = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    cash_inflows = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    cash_outflows = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    expected_cash = Column(Numeric(14, 4), nullable=False)
    actual_cash = Column(Numeric(14, 4), nullable=False)
    difference = Column(Numeric(14, 4), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="closed", nullable=False, index=True)  # closed, reopened
    closed_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reopened_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    reopen_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("business_id", "closing_date", name="uq_cash_closing_business_date"),
    )

    # Relationships
    business = relationship("Business")
    branch = relationship("Branch")
    closed_by_user = relationship("User", foreign_keys=[closed_by_user_id])
    reopened_by_user = relationship("User", foreign_keys=[reopened_by_user_id])
