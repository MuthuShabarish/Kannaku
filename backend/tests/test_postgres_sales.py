import pytest
from decimal import Decimal
import uuid
import threading
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.business import Business, Branch, Warehouse
from app.models.customer import Customer, CustomerLedgerEntry
from app.models.inventory import Category, Product, InventoryBalance, StockMovement
from app.models.sales import Sale, SaleItem, Payment
from app.services.sales_service import create_sale
from app.schemas.sales import SaleCreate, SaleItemCreate


def test_postgres_concurrent_sales_row_locking_prevent_oversell(postgres_engine):
    """
    Simulates concurrent POS checkouts competing for the same limited stock in PostgreSQL 16.
    Uses pessimistic row-locking (SELECT FOR UPDATE) to guarantee that:
    - Exactly one transaction succeeds if requested quantity exceeds total.
    - Negative stock balances are strictly prevented.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    setup_session = Session(postgres_engine)
    try:
        biz = Business(
            name=f"PG Concurrency Biz {uuid.uuid4().hex[:6]}",
            currency_code="INR",
            currency_symbol="₹"
        )
        setup_session.add(biz)
        setup_session.flush()

        branch = Branch(business_id=biz.id, name="Main Branch", is_main=True)
        setup_session.add(branch)
        setup_session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="POS Counter", is_default=True)
        setup_session.add(wh)
        setup_session.flush()

        prod = Product(
            business_id=biz.id,
            name="Limited Edition Watch",
            unit="piece",
            purchase_cost=Decimal("1000.0000"),
            selling_price=Decimal("1500.0000")
        )
        setup_session.add(prod)
        setup_session.flush()

        # Only 10 units in stock
        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("10.0000"),
            average_cost=Decimal("1000.0000")
        )
        setup_session.add(bal)
        setup_session.commit()

        biz_id = biz.id
        prod_id = prod.id
    finally:
        setup_session.close()

    # Two concurrent checkouts both attempting to purchase 7 units (total 14 > 10)
    results = []

    def perform_sale(req_key):
        s = Session(postgres_engine)
        try:
            req = SaleCreate(
                items=[SaleItemCreate(product_id=prod_id, quantity=Decimal("7.0000"))],
                payment_method="cash",
                idempotency_key=req_key
            )
            sale = create_sale(db=s, business_id=biz_id, user_id=None, req=req)
            results.append(("SUCCESS", sale["id"]))
        except Exception as e:
            results.append(("FAILED", str(e)))
        finally:
            s.close()

    t1 = threading.Thread(target=perform_sale, args=("conc-req-1",))
    t2 = threading.Thread(target=perform_sale, args=("conc-req-2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify results: Exactly ONE must succeed and ONE must fail
    successes = [r for r in results if r[0] == "SUCCESS"]
    failures = [r for r in results if r[0] == "FAILED"]

    assert len(successes) == 1, f"Expected exactly 1 success, got: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got: {results}"
    assert "INSUFFICIENT_STOCK" in failures[0][1]

    # Verify final stock in PostgreSQL is exactly 3 units (10 - 7 = 3), NEVER negative
    verify_session = Session(postgres_engine)
    try:
        final_balance = (
            verify_session.query(InventoryBalance)
            .filter(InventoryBalance.business_id == biz_id, InventoryBalance.product_id == prod_id)
            .first()
        )
        assert Decimal(final_balance.current_stock) == Decimal("3.0000")
    finally:
        verify_session.close()


def test_postgres_sale_and_khata_ledger_transactional_integrity(postgres_engine):
    """
    Validates PostgreSQL credit sale creates consistent Sale, SaleItem, StockMovement,
    and CustomerLedgerEntry records with matching references and balances.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz = Business(name=f"PG Khata Biz {uuid.uuid4().hex[:6]}", currency_code="INR")
        session.add(biz)
        session.flush()

        branch = Branch(business_id=biz.id, name="Main Branch", is_main=True)
        session.add(branch)
        session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="Main Counter", is_default=True)
        session.add(wh)
        session.flush()

        cust = Customer(
            business_id=biz.id,
            name="Ramanathan",
            phone=f"9840{uuid.uuid4().int % 1000000:06d}",
            credit_limit=Decimal("5000.0000"),
            current_balance=Decimal("0.0000")
        )
        session.add(cust)
        session.flush()

        prod = Product(
            business_id=biz.id,
            name="Basmati Rice Bag 25kg",
            unit="box",
            purchase_cost=Decimal("1200.0000"),
            selling_price=Decimal("1600.0000")
        )
        session.add(prod)
        session.flush()

        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("20.0000"),
            average_cost=Decimal("1200.0000")
        )
        session.add(bal)
        session.commit()

        # Execute Credit Sale: 2 bags = 3200
        req = SaleCreate(
            customer_id=cust.id,
            items=[SaleItemCreate(product_id=prod.id, quantity=Decimal("2.0000"))],
            payment_method="credit",
            paid_amount=Decimal("0.0000")
        )
        sale_data = create_sale(db=session, business_id=biz.id, user_id=None, req=req)

        # Verify sale in DB
        assert sale_data["credit_amount"] == Decimal("3200.0000")
        assert sale_data["payment_status"] == "unpaid"

        # Verify customer ledger entry
        ledger = (
            session.query(CustomerLedgerEntry)
            .filter(CustomerLedgerEntry.customer_id == cust.id)
            .first()
        )
        assert ledger is not None
        assert ledger.entry_type == "credit_sale"
        assert Decimal(ledger.amount) == Decimal("3200.0000")
        assert Decimal(ledger.balance_after) == Decimal("3200.0000")

        # Verify stock movement
        mov = (
            session.query(StockMovement)
            .filter(StockMovement.product_id == prod.id, StockMovement.movement_type == "sale")
            .first()
        )
        assert mov is not None
        assert Decimal(mov.quantity_delta) == Decimal("-2.0000")
        assert Decimal(mov.balance_after) == Decimal("18.0000")

    finally:
        session.close()
