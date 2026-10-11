import uuid
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class CashLegBreakdown(BaseModel):
    sales_cash_inflows: Decimal = Decimal("0.0000")
    customer_khata_cash_inflows: Decimal = Decimal("0.0000")
    purchase_cash_outflows: Decimal = Decimal("0.0000")
    supplier_settlement_cash_outflows: Decimal = Decimal("0.0000")
    expense_cash_outflows: Decimal = Decimal("0.0000")


class CashClosingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID] = None
    closing_date: date
    session_start: datetime
    session_end: datetime
    opening_cash: Decimal
    cash_inflows: Decimal
    cash_outflows: Decimal
    expected_cash: Decimal
    actual_cash: Decimal
    difference: Decimal
    reconciliation_status: str  # 'reconciled', 'over', 'short'
    notes: Optional[str] = None
    status: str  # 'closed', 'reopened'
    closed_by_user_id: Optional[uuid.UUID] = None
    closed_by_user_name: Optional[str] = None
    reopened_by_user_id: Optional[uuid.UUID] = None
    reopened_at: Optional[datetime] = None
    reopen_reason: Optional[str] = None
    created_at: datetime


class CurrentDrawerStatusResponse(BaseModel):
    closing_date: date
    is_already_closed: bool
    existing_closing_id: Optional[uuid.UUID] = None
    opening_cash: Decimal
    cash_inflows: Decimal
    cash_outflows: Decimal
    expected_cash: Decimal
    breakdown: CashLegBreakdown
    session_start: datetime
    session_end: datetime
    closed_session: Optional[CashClosingResponse] = None


class CashClosingCreate(BaseModel):
    closing_date: date
    opening_cash: Decimal = Field(default=Decimal("0.0000"), ge=0)
    actual_cash: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class CashClosingReopenRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Audit reason for reopening closed cash drawer")
