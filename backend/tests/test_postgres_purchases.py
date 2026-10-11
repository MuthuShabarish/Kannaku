import pytest
from decimal import Decimal
import uuid
import threading
from sqlalchemy.orm import Session

from app.models.business import Business, Branch, Warehouse
from app.models.supplier import Supplier, SupplierLedgerEntry
from app.models.inventory import Product, InventoryBalance, StockMovement
from app.models.purchase import Purchase, PurchaseItem
from app.services.purchase_service import create_purchase
from app.services.supplier_service import record_supplier_payment
from app.schemas.purchase import PurchaseCreate, PurchaseItemCreate
from app.schemas.supplier import SupplierPaymentCreate


def test_postgres_concurrent_purchases_row_locking_mac(postgres_engine):
    """
    Simulates concurrent purchase receipts for the same product in PostgreSQL 16.
    Pessimistic row-locking (with_for_update) guarantees that:
    - Both purchase receipts complete atomically without race conditions.
    - Final stock balance equals initial stock + sum of received quantities.
    - Final Moving Average Cost (MAC) reconciles with the total weighted inventory value.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    setup_session = Session(postgres_engine)
    try:
        biz = Business(
            name=f"PG Concurrency Purchase Biz {uuid.uuid4().hex[:6]}",
            currency_code="INR",
            currency_symbol="₹"
        )
        setup_session.add(biz)
        setup_session.flush()

        branch = Branch(business_id=biz.id, name="Main Branch", is_main=True)
        setup_session.add(branch)
        setup_session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="Central Godown", is_default=True)
        setup_session.add(wh)
        setup_session.flush()

        prod = Product(
            business_id=biz.id,
            name="Structural Steel Beams",
            unit="kg",
            purchase_cost=Decimal("100.0000"),
            selling_price=Decimal("130.0000")
        )
        setup_session.add(prod)
        setup_session.flush()

        # Initial: 10 units @ ₹100 = ₹1,000
        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("10.0000"),
            average_cost=Decimal("100.0000")
        )
        setup_session.add(bal)
        setup_session.commit()

        biz_id = biz.id
        prod_id = prod.id
    finally:
        setup_session.close()

    # Thread 1 purchases 10 units @ ₹200 (value ₹2,000)
    # Thread 2 purchases 10 units @ ₹300 (value ₹3,000)
    results = []

    def perform_purchase(cost_val, req_key):
        s = Session(postgres_engine)
        try:
            req = PurchaseCreate(
                items=[PurchaseItemCreate(product_id=prod_id, quantity=Decimal("10.0000"), unit_cost=cost_val)],
                payment_method="cash",
                idempotency_key=req_key
            )
            p = create_purchase(db=s, business_id=biz_id, user_id=None, req=req)
            results.append(("SUCCESS", p["id"]))
        except Exception as e:
            results.append(("FAILED", str(e)))
        finally:
            s.close()

    t1 = threading.Thread(target=perform_purchase, args=(Decimal("200.0000"), "pg-pur-1"))
    t2 = threading.Thread(target=perform_purchase, args=(Decimal("300.0000"), "pg-pur-2"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both concurrent transactions must succeed due to row-level serialization
    successes = [r for r in results if r[0] == "SUCCESS"]
    assert len(successes) == 2, f"Expected both purchases to succeed, got: {results}"

    # Verify final stock: 10 initial + 10 (t1) + 10 (t2) = 30 units
    # Total inventory value: 10*100 + 10*200 + 10*300 = 1000 + 2000 + 3000 = ₹6,000
    # Final Moving Average Cost: 6000 / 30 = ₹200.0000
    verify_session = Session(postgres_engine)
    try:
        final_balance = (
            verify_session.query(InventoryBalance)
            .filter(InventoryBalance.business_id == biz_id, InventoryBalance.product_id == prod_id)
            .first()
        )
        assert Decimal(final_balance.current_stock) == Decimal("30.0000")
        assert Decimal(final_balance.average_cost) == Decimal("200.0000")
    finally:
        verify_session.close()


def test_postgres_purchase_and_supplier_ap_ledger_transactional_integrity(postgres_engine):
    """
    Validates PostgreSQL credit purchase creates consistent Purchase, PurchaseItem, StockMovement,
    and SupplierLedgerEntry records with matching references and balances.
    Then executes a partial AP settlement and verifies balance decrements and payment records.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable at localhost:5432.")

    session = Session(postgres_engine)
    try:
        biz = Business(name=f"PG AP Ledger Biz {uuid.uuid4().hex[:6]}", currency_code="INR")
        session.add(biz)
        session.flush()

        branch = Branch(business_id=biz.id, name="Main Branch", is_main=True)
        session.add(branch)
        session.flush()

        wh = Warehouse(business_id=biz.id, branch_id=branch.id, name="Main Godown", is_default=True)
        session.add(wh)
        session.flush()

        sup = Supplier(
            business_id=biz.id,
            name="National Cement Mills",
            phone="9840123456",
            current_balance=Decimal("0.0000")
        )
        session.add(sup)
        session.flush()

        prod = Product(
            business_id=biz.id,
            name="Portland Pozzolana Cement 50kg",
            unit="bag",
            purchase_cost=Decimal("380.0000"),
            selling_price=Decimal("430.0000")
        )
        session.add(prod)
        session.flush()

        bal = InventoryBalance(
            business_id=biz.id,
            warehouse_id=wh.id,
            product_id=prod.id,
            current_stock=Decimal("0.0000"),
            average_cost=Decimal("0.0000")
        )
        session.add(bal)
        session.commit()

        # Step 1: Credit purchase of 50 bags @ ₹380 = ₹19,000 (Pay ₹5,000 cash, ₹14,000 on credit)
        req = PurchaseCreate(
            supplier_id=sup.id,
            supplier_invoice_ref="NCM-2026-8801",
            payment_method="credit",
            paid_amount=Decimal("5000.0000"),
            items=[PurchaseItemCreate(product_id=prod.id, quantity=Decimal("50.0000"), unit_cost=Decimal("380.0000"))]
        )
        purchase_data = create_purchase(db=session, business_id=biz.id, user_id=None, req=req)

        assert purchase_data["total_amount"] == Decimal("19000.0000")
        assert purchase_data["paid_amount"] == Decimal("5000.0000")
        assert purchase_data["credit_amount"] == Decimal("14000.0000")
        assert purchase_data["payment_status"] == "partial"

        # Verify supplier balance is ₹14,000
        session.refresh(sup)
        assert sup.current_balance == Decimal("14000.0000")

        # Verify SupplierLedgerEntry
        ledger_entry = (
            session.query(SupplierLedgerEntry)
            .filter(SupplierLedgerEntry.supplier_id == sup.id, SupplierLedgerEntry.entry_type == "credit_purchase")
            .first()
        )
        assert ledger_entry is not None
        assert Decimal(ledger_entry.amount) == Decimal("14000.0000")
        assert Decimal(ledger_entry.balance_after) == Decimal("14000.0000")

        # Step 2: Settle ₹6,000 of the payable via Bank Transfer
        sup, pmt_entry = record_supplier_payment(
            db=session,
            business_id=biz.id,
            supplier_id=sup.id,
            user_id=None,
            req=SupplierPaymentCreate(amount=Decimal("6000.0000"), payment_mode="bank_transfer", notes="NEFT Payment")
        )

        assert sup.current_balance == Decimal("8000.0000")
        assert pmt_entry.balance_after == Decimal("8000.0000")
        assert pmt_entry.entry_type == "payment_made"

        # Verify stock movement
        mov = (
            session.query(StockMovement)
            .filter(StockMovement.product_id == prod.id, StockMovement.movement_type == "purchase")
            .first()
        )
        assert mov is not None
        assert Decimal(mov.quantity_delta) == Decimal("50.0000")
        assert Decimal(mov.balance_after) == Decimal("50.0000")

    finally:
        session.close()
