import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, timezone, date, time
from typing import Optional, List, Tuple, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc, or_
from fastapi import HTTPException, status

from app.models.business import Business, Branch
from app.models.sales import Payment, Sale
from app.models.purchase import Purchase
from app.models.expense import Expense
from app.models.cash_closing import DailyCashClosing
from app.models.user import User
from app.services.reporting_service import get_business_timezone
from app.schemas.cash_closing import (
    CashLegBreakdown,
    CurrentDrawerStatusResponse,
    CashClosingCreate,
    CashClosingResponse,
    CashClosingReopenRequest
)

FOUR_PLACES = Decimal("0.0001")


def get_business_local_today(db: Session, business_id: uuid.UUID) -> date:
    """Returns today's date in the business's configured timezone."""
    tz_str = get_business_timezone(db, business_id)
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")
    return datetime.now(tz).date()


def calculate_physical_cash_movements(
    db: Session,
    business_id: uuid.UUID,
    session_start: datetime,
    session_end: datetime
) -> Tuple[Decimal, Decimal, CashLegBreakdown]:
    """
    Computes strict physical cash inflows and outflows between session_start and session_end.
    Includes only physical cash payment legs ('payment_mode' == 'cash'):
    - Completed sales cash payments (inflow)
    - Customer Khata cash collections (inflow)
    - Non-cancelled purchase cash tender (outflow)
    - Supplier AP cash settlements (outflow)
    - Paid cash operating expenses (outflow)
    Explicitly excludes UPI, Card, and Bank Transfer movements.
    """
    # -------------------------------------------------------------------------
    # 1. Sales Cash Inflows (completed sales only)
    # -------------------------------------------------------------------------
    sales_cash_stmt = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000")))
        .join(Sale, Payment.sale_id == Sale.id)
        .filter(
            Payment.business_id == business_id,
            Payment.payment_direction == "inflow",
            Payment.payment_mode == "cash",
            Payment.sale_id.is_not(None),
            Payment.created_at >= session_start,
            Payment.created_at <= session_end,
            Sale.status == "completed"
        )
    )
    sales_cash_inflow = db.execute(sales_cash_stmt).scalar_one()

    # -------------------------------------------------------------------------
    # 2. Customer Khata Cash Inflows (direct customer collections, sale_id is null)
    # -------------------------------------------------------------------------
    khata_cash_stmt = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000")))
        .filter(
            Payment.business_id == business_id,
            Payment.payment_direction == "inflow",
            Payment.payment_mode == "cash",
            Payment.sale_id.is_(None),
            Payment.customer_id.is_not(None),
            Payment.created_at >= session_start,
            Payment.created_at <= session_end
        )
    )
    khata_cash_inflow = db.execute(khata_cash_stmt).scalar_one()

    # -------------------------------------------------------------------------
    # 3. Purchase Cash Outflows (non-cancelled purchases only)
    # -------------------------------------------------------------------------
    purchase_cash_stmt = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000")))
        .join(Purchase, Payment.purchase_id == Purchase.id)
        .filter(
            Payment.business_id == business_id,
            Payment.payment_direction == "outflow",
            Payment.payment_mode == "cash",
            Payment.purchase_id.is_not(None),
            Payment.created_at >= session_start,
            Payment.created_at <= session_end,
            Purchase.status != "cancelled"
        )
    )
    purchase_cash_outflow = db.execute(purchase_cash_stmt).scalar_one()

    # -------------------------------------------------------------------------
    # 4. Supplier Settlement Cash Outflows (direct AP payments, purchase_id is null)
    # -------------------------------------------------------------------------
    supplier_cash_stmt = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000")))
        .filter(
            Payment.business_id == business_id,
            Payment.payment_direction == "outflow",
            Payment.payment_mode == "cash",
            Payment.purchase_id.is_(None),
            Payment.supplier_id.is_not(None),
            Payment.created_at >= session_start,
            Payment.created_at <= session_end
        )
    )
    supplier_cash_outflow = db.execute(supplier_cash_stmt).scalar_one()

    # -------------------------------------------------------------------------
    # 5. Operating Expense Cash Outflows (paid cash expenses, non-voided)
    # -------------------------------------------------------------------------
    expense_cash_stmt = (
        select(func.coalesce(func.sum(Expense.amount), Decimal("0.0000")))
        .filter(
            Expense.business_id == business_id,
            Expense.payment_method == "cash",
            Expense.payment_status == "paid",
            Expense.voided_at.is_(None),
            Expense.expense_date >= session_start,
            Expense.expense_date <= session_end
        )
    )
    expense_cash_outflow = db.execute(expense_cash_stmt).scalar_one()

    total_inflows = (sales_cash_inflow + khata_cash_inflow).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    total_outflows = (purchase_cash_outflow + supplier_cash_outflow + expense_cash_outflow).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    breakdown = CashLegBreakdown(
        sales_cash_inflows=sales_cash_inflow,
        customer_khata_cash_inflows=khata_cash_inflow,
        purchase_cash_outflows=purchase_cash_outflow,
        supplier_settlement_cash_outflows=supplier_cash_outflow,
        expense_cash_outflows=expense_cash_outflow
    )

    return total_inflows, total_outflows, breakdown


def _to_closing_response(c: DailyCashClosing) -> CashClosingResponse:
    rec_status = "reconciled"
    if c.difference > Decimal("0.0000"):
        rec_status = "over"
    elif c.difference < Decimal("0.0000"):
        rec_status = "short"

    user_name = c.closed_by_user.full_name if c.closed_by_user else None

    return CashClosingResponse(
        id=c.id,
        business_id=c.business_id,
        branch_id=c.branch_id,
        closing_date=c.closing_date,
        session_start=c.session_start,
        session_end=c.session_end,
        opening_cash=c.opening_cash,
        cash_inflows=c.cash_inflows,
        cash_outflows=c.cash_outflows,
        expected_cash=c.expected_cash,
        actual_cash=c.actual_cash,
        difference=c.difference,
        reconciliation_status=rec_status,
        notes=c.notes,
        status=c.status,
        closed_by_user_id=c.closed_by_user_id,
        closed_by_user_name=user_name,
        reopened_by_user_id=c.reopened_by_user_id,
        reopened_at=c.reopened_at,
        reopen_reason=c.reopen_reason,
        created_at=c.created_at
    )


def get_current_drawer_status(
    db: Session,
    business_id: uuid.UUID,
    target_date: Optional[date] = None
) -> CurrentDrawerStatusResponse:
    """
    Returns current cash drawer state for the business-local date.
    If the drawer for this date is already closed, returns closed session details.
    Otherwise, computes opening cash, real-time physical cash movements, and expected closing cash.
    """
    if target_date is None:
        target_date = get_business_local_today(db, business_id)

    tz_str = get_business_timezone(db, business_id)
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    # Check if a closing session already exists for this date
    existing_closing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.business_id == business_id,
            DailyCashClosing.closing_date == target_date
        )
        .first()
    )

    if existing_closing and existing_closing.status == "closed":
        resp = _to_closing_response(existing_closing)
        _, _, breakdown = calculate_physical_cash_movements(
            db, business_id, existing_closing.session_start, existing_closing.session_end
        )
        return CurrentDrawerStatusResponse(
            closing_date=target_date,
            is_already_closed=True,
            existing_closing_id=existing_closing.id,
            opening_cash=existing_closing.opening_cash,
            cash_inflows=existing_closing.cash_inflows,
            cash_outflows=existing_closing.cash_outflows,
            expected_cash=existing_closing.expected_cash,
            breakdown=breakdown,
            session_start=existing_closing.session_start,
            session_end=existing_closing.session_end,
            closed_session=resp
        )

    # Drawer is open for this date. Determine session bounds & opening float.
    # Look for most recent closed session prior to this target_date
    prev_closing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.business_id == business_id,
            DailyCashClosing.closing_date < target_date,
            DailyCashClosing.status == "closed"
        )
        .order_by(DailyCashClosing.closing_date.desc(), DailyCashClosing.session_end.desc())
        .first()
    )

    if prev_closing:
        opening_cash = prev_closing.actual_cash
        session_start = prev_closing.session_end
    else:
        # First session for business: start at beginning of target_date in local timezone
        opening_cash = Decimal("0.0000")
        start_local = datetime.combine(target_date, time(0, 0, 0, 0)).replace(tzinfo=tz)
        session_start = start_local.astimezone(timezone.utc)

    # Current cutoff time is right now (in UTC)
    session_end = datetime.now(timezone.utc)
    if session_end < session_start:
        session_end = session_start

    inflows, outflows, breakdown = calculate_physical_cash_movements(
        db, business_id, session_start, session_end
    )
    expected_cash = (opening_cash + inflows - outflows).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    closed_session_resp = _to_closing_response(existing_closing) if existing_closing else None

    return CurrentDrawerStatusResponse(
        closing_date=target_date,
        is_already_closed=False,
        existing_closing_id=existing_closing.id if existing_closing else None,
        opening_cash=opening_cash,
        cash_inflows=inflows,
        cash_outflows=outflows,
        expected_cash=expected_cash,
        breakdown=breakdown,
        session_start=session_start,
        session_end=session_end,
        closed_session=closed_session_resp
    )


def close_cash_drawer(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    req: CashClosingCreate
) -> CashClosingResponse:
    """
    Executes atomic daily physical cash closing:
    - Verifies no existing closed session for the date (preventing duplicate closes)
    - Establishes immutable session cutoff
    - Computes authoritative cash inflows, outflows, expected cash and reconciliation difference
    - Persists DailyCashClosing record with full audit metadata
    """
    # 1. Row locking / check existing record for this date
    existing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.business_id == business_id,
            DailyCashClosing.closing_date == req.closing_date
        )
        .with_for_update()
        .first()
    )

    if existing and existing.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_CLOSED",
                "message": f"Daily cash drawer for {req.closing_date} has already been closed.",
                "closing_id": str(existing.id)
            }
        )

    # 2. Determine session start
    prev_closing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.business_id == business_id,
            DailyCashClosing.closing_date < req.closing_date,
            DailyCashClosing.status == "closed"
        )
        .order_by(DailyCashClosing.closing_date.desc(), DailyCashClosing.session_end.desc())
        .first()
    )

    tz_str = get_business_timezone(db, business_id)
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    if prev_closing:
        session_start = prev_closing.session_end
    else:
        start_local = datetime.combine(req.closing_date, time(0, 0, 0, 0)).replace(tzinfo=tz)
        session_start = start_local.astimezone(timezone.utc)

    # Cutoff timestamp is exact execution moment
    session_end = datetime.now(timezone.utc)
    if session_end < session_start:
        session_end = session_start

    # 3. Calculate authoritative physical cash legs
    inflows, outflows, _ = calculate_physical_cash_movements(
        db, business_id, session_start, session_end
    )

    opening_cash = req.opening_cash.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    actual_cash = req.actual_cash.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    expected_cash = (opening_cash + inflows - outflows).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    difference = (actual_cash - expected_cash).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    # 4. Save or update record
    if existing and existing.status == "reopened":
        closing_obj = existing
        closing_obj.session_start = session_start
        closing_obj.session_end = session_end
        closing_obj.opening_cash = opening_cash
        closing_obj.cash_inflows = inflows
        closing_obj.cash_outflows = outflows
        closing_obj.expected_cash = expected_cash
        closing_obj.actual_cash = actual_cash
        closing_obj.difference = difference
        closing_obj.notes = req.notes.strip() if req.notes else None
        closing_obj.status = "closed"
        closing_obj.closed_by_user_id = user_id
    else:
        closing_obj = DailyCashClosing(
            business_id=business_id,
            closing_date=req.closing_date,
            session_start=session_start,
            session_end=session_end,
            opening_cash=opening_cash,
            cash_inflows=inflows,
            cash_outflows=outflows,
            expected_cash=expected_cash,
            actual_cash=actual_cash,
            difference=difference,
            notes=req.notes.strip() if req.notes else None,
            status="closed",
            closed_by_user_id=user_id
        )
        db.add(closing_obj)

    try:
        db.commit()
        db.refresh(closing_obj)
        return _to_closing_response(closing_obj)
    except Exception:
        db.rollback()
        raise


def reopen_cash_closing(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    closing_id: uuid.UUID,
    reason: str
) -> CashClosingResponse:
    """
    Auditable cash closing reopening policy:
    Allows authorized correction without silent tampering, capturing mandatory justification.
    """
    clean_reason = reason.strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "REASON_REQUIRED", "message": "A non-empty audit reason is mandatory to reopen a closed drawer."}
        )

    closing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.id == closing_id,
            DailyCashClosing.business_id == business_id
        )
        .with_for_update()
        .first()
    )

    if not closing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLOSING_NOT_FOUND", "message": "Cash closing session not found."}
        )

    if closing.status == "reopened":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ALREADY_REOPENED", "message": "This cash closing session is already open for correction."}
        )

    closing.status = "reopened"
    closing.reopened_by_user_id = user_id
    closing.reopened_at = datetime.now(timezone.utc)
    closing.reopen_reason = clean_reason

    try:
        db.commit()
        db.refresh(closing)
        return _to_closing_response(closing)
    except Exception:
        db.rollback()
        raise


def get_cash_closing_history(
    db: Session,
    business_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 30,
    offset: int = 0
) -> Tuple[List[CashClosingResponse], int]:
    """Retrieves paginated historical cash closing records for the business."""
    query = db.query(DailyCashClosing).filter(DailyCashClosing.business_id == business_id)

    if start_date:
        query = query.filter(DailyCashClosing.closing_date >= start_date)
    if end_date:
        query = query.filter(DailyCashClosing.closing_date <= end_date)

    total = query.count()
    records = query.order_by(DailyCashClosing.closing_date.desc(), DailyCashClosing.created_at.desc()).offset(offset).limit(limit).all()

    return [_to_closing_response(r) for r in records], total


def get_cash_closing_detail(
    db: Session,
    business_id: uuid.UUID,
    closing_id: uuid.UUID
) -> Tuple[CashClosingResponse, CashLegBreakdown]:
    """Retrieves full detail and movement breakdown for a specific cash closing session."""
    closing = (
        db.query(DailyCashClosing)
        .filter(
            DailyCashClosing.id == closing_id,
            DailyCashClosing.business_id == business_id
        )
        .first()
    )

    if not closing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLOSING_NOT_FOUND", "message": "Cash closing session not found."}
        )

    _, _, breakdown = calculate_physical_cash_movements(
        db, business_id, closing.session_start, closing.session_end
    )
    return _to_closing_response(closing), breakdown
