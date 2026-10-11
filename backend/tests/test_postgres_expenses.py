import pytest
from decimal import Decimal
import uuid
import threading
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.business import Business, Branch, Warehouse
from app.models.expense import ExpenseCategory, Expense
from app.services.expense_service import create_expense, get_expense_overview
from app.services.cashbook_service import get_cashbook_transactions, get_cashbook_summary
from app.schemas.expense import ExpenseCreate


def test_postgres_atomic_expense_concurrency_and_idempotency(postgres_engine):
    """
    Simulates concurrent thread submissions of expenses with the same idempotency key
    against native PostgreSQL 16 to verify unique constraint and atomic consistency.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    setup_session = Session(postgres_engine)
    try:
        biz = Business(
            name=f"PG Concurrency Expense Biz {uuid.uuid4().hex[:6]}",
            currency_code="INR",
            currency_symbol="₹"
        )
        setup_session.add(biz)
        setup_session.flush()

        cat = ExpenseCategory(
            business_id=biz.id,
            name="Packaging Material",
            description="Cartons and tape",
            is_active=True
        )
        setup_session.add(cat)
        setup_session.commit()

        biz_id = biz.id
        cat_id = cat.id
    finally:
        setup_session.close()

    results = []
    errors = []

    def submit_expense(thread_idx):
        thread_session = Session(postgres_engine)
        try:
            req = ExpenseCreate(
                category_id=cat_id,
                amount=Decimal("3500.0000"),
                payment_method="cash",
                payment_status="paid",
                description="Heavy duty packing boxes",
                idempotency_key="pg-pack-boxes-unique"
            )
            exp = create_expense(
                db=thread_session,
                business_id=biz_id,
                user_id=None,
                data=req
            )
            results.append(exp.id)
        except Exception as e:
            errors.append(str(e))
        finally:
            thread_session.close()

    t1 = threading.Thread(target=submit_expense, args=(1,))
    t2 = threading.Thread(target=submit_expense, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify in DB: exactly 1 expense row should exist!
    check_session = Session(postgres_engine)
    try:
        count = check_session.execute(
            select(func.count(Expense.id)).filter(
                Expense.business_id == biz_id,
                Expense.idempotency_key == "pg-pack-boxes-unique"
            )
        ).scalar_one()
        assert count == 1, f"Expected exactly 1 expense row, found {count}"
    finally:
        check_session.close()


def test_postgres_cashbook_reconciliation_and_cross_tenant_isolation(postgres_engine):
    """
    Verifies that cashbook queries in PostgreSQL 16:
    1. Reconcile accurately with NUMERIC(14, 4) exact decimal calculations.
    2. Maintain strict multi-tenant boundary isolation between two concurrent businesses.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz_a = Business(name=f"PG Tenant A {uuid.uuid4().hex[:6]}", currency_code="INR", currency_symbol="₹")
        biz_b = Business(name=f"PG Tenant B {uuid.uuid4().hex[:6]}", currency_code="INR", currency_symbol="₹")
        session.add_all([biz_a, biz_b])
        session.flush()

        cat_a = ExpenseCategory(business_id=biz_a.id, name="Shop Rent", is_active=True)
        cat_b = ExpenseCategory(business_id=biz_b.id, name="Shop Rent", is_active=True)
        session.add_all([cat_a, cat_b])
        session.flush()

        # Add paid expense to Tenant A
        exp_a = Expense(
            business_id=biz_a.id,
            category_id=cat_a.id,
            expense_number="EXP-20261011-0001",
            amount=Decimal("12000.0000"),
            payment_method="bank_transfer",
            payment_status="paid",
            description="Tenant A Monthly Rent"
        )
        # Add paid expense to Tenant B
        exp_b = Expense(
            business_id=biz_b.id,
            category_id=cat_b.id,
            expense_number="EXP-20261011-0001",
            amount=Decimal("5000.0000"),
            payment_method="cash",
            payment_status="paid",
            description="Tenant B Monthly Rent"
        )
        session.add_all([exp_a, exp_b])
        session.commit()

        # Query Tenant A cashbook
        summary_a = get_cashbook_summary(session, biz_a.id)
        assert summary_a.total_outflows == Decimal("12000.0000")
        assert summary_a.net_cash_movement == Decimal("-12000.0000")
        assert summary_a.transaction_count == 1

        txs_a, count_a = get_cashbook_transactions(session, biz_a.id)
        assert count_a == 1
        assert txs_a[0].amount == Decimal("12000.0000")
        assert txs_a[0].party_name == "Operating Expense"

        # Query Tenant B cashbook
        summary_b = get_cashbook_summary(session, biz_b.id)
        assert summary_b.total_outflows == Decimal("5000.0000")
        assert summary_b.net_cash_movement == Decimal("-5000.0000")
        assert summary_b.transaction_count == 1

        txs_b, count_b = get_cashbook_transactions(session, biz_b.id)
        assert count_b == 1
        assert txs_b[0].amount == Decimal("5000.0000")
    finally:
        session.close()
