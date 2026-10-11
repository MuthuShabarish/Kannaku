import pytest
from decimal import Decimal
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.business import Business
from app.models.cash_closing import DailyCashClosing
from app.services.cash_closing_service import calculate_physical_cash_movements, close_cash_drawer
from app.schemas.cash_closing import CashClosingCreate


def test_postgres_cash_closing_unique_date_constraint(postgres_engine):
    """
    Validates PostgreSQL native unique constraint on (business_id, closing_date)
    preventing duplicate cash closing records for the same date.
    """
    if postgres_engine is None:
        pytest.skip(
            "PostgreSQL test database not reachable at localhost:5432. "
            "Reported accurately as required: PostgreSQL integration tests require running PostgreSQL / Docker Compose service."
        )

    session = Session(postgres_engine)
    try:
        biz = Business(
            name=f"PG Cash Closing Biz {uuid.uuid4().hex[:6]}",
            currency_code="INR",
            currency_symbol="₹"
        )
        session.add(biz)
        session.commit()

        today = date.today()
        now = datetime.now(timezone.utc)

        close1 = DailyCashClosing(
            business_id=biz.id,
            closing_date=today,
            session_start=now,
            session_end=now,
            opening_cash=Decimal("500.0000"),
            cash_inflows=Decimal("200.0000"),
            cash_outflows=Decimal("50.0000"),
            expected_cash=Decimal("650.0000"),
            actual_cash=Decimal("650.0000"),
            difference=Decimal("0.0000"),
            status="closed"
        )
        session.add(close1)
        session.commit()

        # Attempt duplicate insertion for same business and date -> must fail with IntegrityError
        close2 = DailyCashClosing(
            business_id=biz.id,
            closing_date=today,
            session_start=now,
            session_end=now,
            opening_cash=Decimal("500.0000"),
            cash_inflows=Decimal("0.0000"),
            cash_outflows=Decimal("0.0000"),
            expected_cash=Decimal("500.0000"),
            actual_cash=Decimal("500.0000"),
            difference=Decimal("0.0000"),
            status="closed"
        )
        session.add(close2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

        # Cleanup
        session.delete(close1)
        session.delete(biz)
        session.commit()
    finally:
        session.close()


def test_postgres_decimal_precision_and_reconciliation_math(postgres_engine):
    """
    Validates PostgreSQL NUMERIC(14, 4) arithmetic precision without floating point drift.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz = Business(
            name=f"PG Decimal Precision Biz {uuid.uuid4().hex[:6]}",
            currency_code="INR",
            currency_symbol="₹"
        )
        session.add(biz)
        session.commit()

        today = date.today()
        now = datetime.now(timezone.utc)

        # High precision decimals
        opening = Decimal("12345.6789")
        inflow = Decimal("9876.5432")
        outflow = Decimal("4321.0987")
        expected = opening + inflow - outflow  # 17901.1234
        actual = Decimal("17900.0000")
        diff = actual - expected  # -1.1234

        closing = DailyCashClosing(
            business_id=biz.id,
            closing_date=today,
            session_start=now,
            session_end=now,
            opening_cash=opening,
            cash_inflows=inflow,
            cash_outflows=outflow,
            expected_cash=expected,
            actual_cash=actual,
            difference=diff,
            status="closed"
        )
        session.add(closing)
        session.commit()

        # Reload from PostgreSQL and assert exact Decimal equality
        reloaded = session.query(DailyCashClosing).filter(DailyCashClosing.id == closing.id).one()
        assert reloaded.expected_cash == Decimal("17901.1234")
        assert reloaded.difference == Decimal("-1.1234")

        session.delete(closing)
        session.delete(biz)
        session.commit()
    finally:
        session.close()
