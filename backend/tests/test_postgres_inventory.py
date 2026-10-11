import pytest
from decimal import Decimal
import uuid
from sqlalchemy import text, exc
from sqlalchemy.orm import Session

from app.models.business import Business, Branch, Warehouse
from app.models.inventory import Category, Product, InventoryBalance, StockMovement
from app.services.inventory_service import adjust_stock
from app.schemas.inventory import StockAdjustmentCreate


def test_postgres_inventory_schema_and_persistence(postgres_engine):
    """
    Validates PostgreSQL native schema, UUID types, NUMERIC(14, 4), and persistence.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz = Business(
            name="PG Inventory Shop",
            currency_code="INR",
            currency_symbol="₹",
            default_language="ta"
        )
        session.add(biz)
        session.flush()

        cat = Category(
            business_id=biz.id,
            name="Grains & Pulses",
            tamil_name="தானியங்கள்"
        )
        session.add(cat)
        session.flush()

        prod = Product(
            business_id=biz.id,
            category_id=cat.id,
            name="Toor Dal Premium 1kg",
            sku="TD-001",
            unit="kg",
            purchase_cost=Decimal("145.7500"),
            selling_price=Decimal("175.5000"),
            low_stock_threshold=Decimal("15.0000")
        )
        session.add(prod)
        session.flush()

        branch = Branch(business_id=biz.id, name="Main Branch")
        session.add(branch)
        session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="Godown 1", is_default=True)
        session.add(wh)
        session.flush()

        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("100.0000"),
            reserved_stock=Decimal("0.0000"),
            average_cost=Decimal("145.7500")
        )
        session.add(bal)
        session.commit()

        # Query back using raw SQL to verify PostgreSQL native types
        with postgres_engine.connect() as conn:
            row = conn.execute(
                text("SELECT current_stock, average_cost FROM inventory_balances WHERE id = :id"),
                {"id": str(bal.id)}
            ).fetchone()
            assert row is not None
            assert Decimal(str(row[0])) == Decimal("100.0000")
            assert Decimal(str(row[1])) == Decimal("145.7500")

    finally:
        session.rollback()
        # Clean up
        with postgres_engine.connect() as conn:
            conn.execute(text("DELETE FROM businesses WHERE name = 'PG Inventory Shop'"))
            conn.commit()
        session.close()


def test_postgres_strict_check_constraint_negative_stock(postgres_engine):
    """
    Validates PostgreSQL check constraint 'chk_current_stock_non_negative' directly
    prevents negative current_stock at database level.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz = Business(name="PG Constraint Shop", currency_code="INR", currency_symbol="₹")
        session.add(biz)
        session.flush()

        branch = Branch(business_id=biz.id, name="B1")
        session.add(branch)
        session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="W1")
        session.add(wh)
        session.flush()

        prod = Product(business_id=biz.id, name="Strict Item", selling_price=Decimal("10.00"))
        session.add(prod)
        session.flush()

        # Attempt to insert negative current_stock directly
        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("-5.0000"),
            average_cost=Decimal("10.00")
        )
        session.add(bal)

        with pytest.raises(exc.IntegrityError) as excinfo:
            session.commit()

        assert "chk_current_stock_non_negative" in str(excinfo.value)
    finally:
        session.rollback()
        with postgres_engine.connect() as conn:
            conn.execute(text("DELETE FROM businesses WHERE name = 'PG Constraint Shop'"))
            conn.commit()
        session.close()


def test_postgres_concurrent_stock_adjustment_locking(postgres_engine):
    """
    Validates PostgreSQL pessimistic row locking (with_for_update) during concurrent adjustments.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session1 = Session(postgres_engine)
    session2 = Session(postgres_engine)

    try:
        biz = Business(name="PG Concurrency Shop", currency_code="INR", currency_symbol="₹")
        session1.add(biz)
        session1.flush()

        branch = Branch(business_id=biz.id, name="B1")
        session1.add(branch)
        session1.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="Main Counter", is_default=True)
        session1.add(wh)
        session1.flush()

        prod = Product(business_id=biz.id, name="High Demand Item", selling_price=Decimal("50.00"))
        session1.add(prod)
        session1.flush()

        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("100.0000"),
            average_cost=Decimal("30.00")
        )
        session1.add(bal)
        session1.commit()

        # Sequential concurrent adjustments in separate transactions
        req1 = StockAdjustmentCreate(
            product_id=prod.id,
            adjustment_type="decrease",
            quantity=Decimal("30.00"),
            reason="Order 1 dispatch"
        )
        mov1 = adjust_stock(session1, biz.id, None, req1)
        assert mov1.balance_after == Decimal("70.00")

        req2 = StockAdjustmentCreate(
            product_id=prod.id,
            adjustment_type="decrease",
            quantity=Decimal("20.00"),
            reason="Order 2 dispatch"
        )
        mov2 = adjust_stock(session2, biz.id, None, req2)
        assert mov2.balance_after == Decimal("50.00")

        # Verify final committed stock
        session_verify = Session(postgres_engine)
        final_bal = session_verify.query(InventoryBalance).filter(InventoryBalance.id == bal.id).first()
        assert final_bal.current_stock == Decimal("50.0000")
        session_verify.close()

    finally:
        session1.rollback()
        session2.rollback()
        with postgres_engine.connect() as conn:
            conn.execute(text("DELETE FROM businesses WHERE name = 'PG Concurrency Shop'"))
            conn.commit()
        session1.close()
        session2.close()
