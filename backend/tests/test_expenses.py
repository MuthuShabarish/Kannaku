import pytest
from decimal import Decimal
import uuid
from starlette.testclient import TestClient


def register_user(client: TestClient, phone: str, business_name: str) -> dict:
    reg_res = client.post("/api/v1/auth/register", json={
        "phone": phone,
        "full_name": f"Owner {phone}",
        "pin_or_password": "1234SecurePassword!",
        "business_name": business_name,
        "category": "retail",
        "currency_code": "INR",
        "currency_symbol": "₹",
        "default_language": "ta"
    })
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["data"]["tokens"]["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "business_id": reg_res.json()["data"]["business"]["id"],
        "user_id": reg_res.json()["data"]["user"]["id"]
    }


def create_sample_product(client: TestClient, headers: dict, name: str, cost: str, price: str, stock: str) -> dict:
    res = client.post("/api/v1/products", headers=headers, json={
        "name": name,
        "unit": "piece",
        "purchase_cost": cost,
        "selling_price": price,
        "opening_stock": stock,
        "opening_stock_cost": cost
    })
    assert res.status_code == 201, res.text
    return res.json()["data"]


# ============================================================================
# 1. EXPENSE CATEGORIES TESTS
# ============================================================================

def test_expense_categories_lifecycle_and_default_seeding(client: TestClient):
    auth = register_user(client, "9876541001", "Murugan Bakery")
    headers = auth["headers"]

    # 1. First fetch should auto-seed standard default categories
    res = client.get("/api/v1/expense-categories", headers=headers)
    assert res.status_code == 200
    cats = res.json()["data"]
    assert len(cats) >= 9
    cat_names = [c["name"] for c in cats]
    assert "Rent" in cat_names
    assert "Electricity & Utilities" in cat_names
    assert "Staff Wages" in cat_names

    # 2. Create custom category
    custom_res = client.post("/api/v1/expense-categories", headers=headers, json={
        "name": "Baking Fuel & Gas",
        "description": "LPG cylinders and oven fuel"
    })
    assert custom_res.status_code == 201
    custom_id = custom_res.json()["data"]["id"]
    assert custom_res.json()["data"]["name"] == "Baking Fuel & Gas"
    assert custom_res.json()["data"]["is_system_default"] is False

    # 3. Reject duplicate category name in same business
    dup_res = client.post("/api/v1/expense-categories", headers=headers, json={
        "name": "baking fuel & gas"
    })
    assert dup_res.status_code == 400
    assert dup_res.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"

    # 4. Update category
    upd_res = client.put(f"/api/v1/expense-categories/{custom_id}", headers=headers, json={
        "description": "Commercial LPG cylinders only",
        "is_active": False
    })
    assert upd_res.status_code == 200
    assert upd_res.json()["data"]["description"] == "Commercial LPG cylinders only"
    assert upd_res.json()["data"]["is_active"] is False

    # 5. Delete category when unused
    del_res = client.delete(f"/api/v1/expense-categories/{custom_id}", headers=headers)
    assert del_res.status_code == 200


# ============================================================================
# 2. EXPENSE RECORDING & VALIDATION TESTS
# ============================================================================

def test_expense_recording_and_validation(client: TestClient):
    auth = register_user(client, "9876541002", "Annamalai Textiles")
    headers = auth["headers"]

    # Get Rent category
    cats_res = client.get("/api/v1/expense-categories", headers=headers)
    rent_cat = next(c for c in cats_res.json()["data"] if c["name"] == "Rent")

    # 1. Record valid cash expense
    exp_res = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": rent_cat["id"],
        "amount": "15000.00",
        "payment_method": "bank_transfer",
        "payment_status": "paid",
        "payee": "Sri Lakshmi Real Estates",
        "description": "October 2026 shop building rent",
        "reference_number": "UTR-RENT-OCT26",
        "idempotency_key": "rent-oct-2026"
    })
    assert exp_res.status_code == 201
    exp_data = exp_res.json()["data"]
    assert exp_data["expense_number"].startswith("EXP-")
    assert Decimal(exp_data["amount"]) == Decimal("15000.0000")
    assert exp_data["category_name"] == "Rent"
    assert exp_data["payment_status"] == "paid"

    # 2. Reject negative or zero amount
    neg_res = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": rent_cat["id"],
        "amount": "-500.00",
        "description": "Invalid negative expense"
    })
    assert neg_res.status_code == 422 or neg_res.status_code == 400

    # 3. Reject expense on inactive category
    # Deactivate Rent category
    client.put(f"/api/v1/expense-categories/{rent_cat['id']}", headers=headers, json={"is_active": False})
    inact_res = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": rent_cat["id"],
        "amount": "500.00",
        "description": "Should fail on inactive category"
    })
    assert inact_res.status_code == 400
    assert inact_res.json()["error"]["code"] == "CATEGORY_INACTIVE"

    # Reactivate Rent category
    client.put(f"/api/v1/expense-categories/{rent_cat['id']}", headers=headers, json={"is_active": True})

    # 4. Filter and search expenses
    list_res = client.get("/api/v1/expenses", headers=headers, params={"search": "Sri Lakshmi"})
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1
    assert list_res.json()["data"][0]["payee"] == "Sri Lakshmi Real Estates"


# ============================================================================
# 3. EXPENSE VOIDING & EXCLUSION FROM ACTIVE TOTALS
# ============================================================================

def test_expense_voiding_and_exclusion_from_active_totals(client: TestClient):
    auth = register_user(client, "9876541003", "Kavitha Provisions")
    headers = auth["headers"]

    cats_res = client.get("/api/v1/expense-categories", headers=headers)
    elec_cat = next(c for c in cats_res.json()["data"] if c["name"] == "Electricity & Utilities")
    tea_cat = next(c for c in cats_res.json()["data"] if c["name"] == "Miscellaneous")

    # Record two expenses
    e1 = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": elec_cat["id"],
        "amount": "2500.00",
        "description": "TNEB EB electricity bill",
        "payment_method": "upi"
    }).json()["data"]

    e2 = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": tea_cat["id"],
        "amount": "300.00",
        "description": "Customer tea and coffee",
        "payment_method": "cash"
    }).json()["data"]

    # Initial overview: total should be 2800.00
    ov_init = client.get("/api/v1/expenses/overview", headers=headers).json()["data"]
    assert Decimal(ov_init["total_expenses"]) == Decimal("2800.0000")
    assert ov_init["total_count"] == 2

    # Void e2 (miscellaneous tea expense)
    void_res = client.post(f"/api/v1/expenses/{e2['id']}/void", headers=headers, json={
        "reason": "Mistaken duplicate entry by cashier"
    })
    assert void_res.status_code == 200
    assert void_res.json()["data"]["payment_status"] == "voided"
    assert void_res.json()["data"]["void_reason"] == "Mistaken duplicate entry by cashier"
    assert void_res.json()["data"]["voided_at"] is not None

    # Overview after voiding: total should now only be 2500.00 (e2 completely excluded!)
    ov_after = client.get("/api/v1/expenses/overview", headers=headers).json()["data"]
    assert Decimal(ov_after["total_expenses"]) == Decimal("2500.0000")
    assert ov_after["total_count"] == 1

    # Cannot edit or re-void a voided expense
    cant_edit = client.put(f"/api/v1/expenses/{e2['id']}", headers=headers, json={"description": "Try editing"})
    assert cant_edit.status_code == 400
    assert cant_edit.json()["error"]["code"] == "CANNOT_EDIT_VOIDED_EXPENSE"

    cant_revoid = client.post(f"/api/v1/expenses/{e2['id']}/void", headers=headers, json={"reason": "Void again"})
    assert cant_revoid.status_code == 400
    assert cant_revoid.json()["error"]["code"] == "EXPENSE_ALREADY_VOIDED"


# ============================================================================
# 4. IDEMPOTENCY & CROSS-TENANT ISOLATION
# ============================================================================

def test_expense_idempotency_and_tenant_isolation(client: TestClient):
    auth1 = register_user(client, "9876541004", "Tenant Alpha")
    auth2 = register_user(client, "9876541005", "Tenant Beta")

    cats1 = client.get("/api/v1/expense-categories", headers=auth1["headers"]).json()["data"]
    cat1_id = cats1[0]["id"]

    # 1. Idempotency test for Tenant Alpha
    exp1 = client.post("/api/v1/expenses", headers=auth1["headers"], json={
        "category_id": cat1_id,
        "amount": "1200.00",
        "description": "Stationery supplies",
        "idempotency_key": "alpha-stat-001"
    }).json()["data"]

    # Repeat same request
    exp1_repeat = client.post("/api/v1/expenses", headers=auth1["headers"], json={
        "category_id": cat1_id,
        "amount": "1200.00",
        "description": "Stationery supplies",
        "idempotency_key": "alpha-stat-001"
    }).json()["data"]
    assert exp1["id"] == exp1_repeat["id"]

    # 2. Cross-tenant access isolation
    # Tenant Beta cannot access Tenant Alpha's expense
    denied_res = client.get(f"/api/v1/expenses/{exp1['id']}", headers=auth2["headers"])
    assert denied_res.status_code == 404

    # Tenant Beta cannot void Tenant Alpha's expense
    denied_void = client.post(f"/api/v1/expenses/{exp1['id']}/void", headers=auth2["headers"], json={"reason": "Hacking"})
    assert denied_void.status_code == 404


# ============================================================================
# 5. CASHBOOK INFLOWS, OUTFLOWS & ZERO DOUBLE-COUNTING RECONCILIATION
# ============================================================================

def test_cashbook_inflows_outflows_and_reconciliation(client: TestClient):
    auth = register_user(client, "9876541006", "Comprehensive Cashbook Store")
    headers = auth["headers"]

    # Create Product
    prod = create_sample_product(client, headers, "Cooking Oil 1L", "100.00", "150.00", "100")
    prod_id = prod["id"]

    # Create Customer
    cust_res = client.post("/api/v1/customers", headers=headers, json={"name": "Ramu G", "phone": "9876543210", "credit_limit": "5000.00"})
    cust_id = cust_res.json()["data"]["id"]

    # Create Supplier
    sup_res = client.post("/api/v1/suppliers", headers=headers, json={"name": "Oil Mills Corp"})
    sup_id = sup_res.json()["data"]["id"]

    # --- 1. Immediate Cash Sale: 2 units @ ₹150 = ₹300 paid in Cash ---
    sale1_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod_id, "quantity": "2", "unit_price": "150.00"}],
        "payment_method": "cash",
        "paid_amount": "300.00"
    })
    assert sale1_res.status_code == 201

    # --- 2. Credit Sale (Udhar): 2 units @ ₹150 = ₹300, ₹0 paid ---
    # MUST NOT create cash inflow!
    sale2_res = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust_id,
        "items": [{"product_id": prod_id, "quantity": "2", "unit_price": "150.00"}],
        "payment_method": "credit",
        "paid_amount": "0.00"
    })
    assert sale2_res.status_code == 201

    # Verify Cashbook at this point:
    cb1 = client.get("/api/v1/cashbook/summary", headers=headers).json()["data"]
    assert Decimal(cb1["total_inflows"]) == Decimal("300.0000")  # Only the paid sale!
    assert Decimal(cb1["total_outflows"]) == Decimal("0.0000")

    # --- 3. Later Customer Khata Payment: ₹200 via UPI ---
    # Enters cashbook now!
    khata_pay = client.post(f"/api/v1/customers/{cust_id}/payments", headers=headers, json={
        "amount": "200.00",
        "payment_mode": "upi",
        "notes": "Ramu part payment"
    })
    assert khata_pay.status_code == 201

    cb2 = client.get("/api/v1/cashbook/summary", headers=headers).json()["data"]
    assert Decimal(cb2["total_inflows"]) == Decimal("500.0000")  # 300 cash sale + 200 UPI settlement

    # --- 4. Immediate Purchase: 5 units @ ₹100 = ₹500 paid in Cash ---
    pur1_res = client.post("/api/v1/purchases", headers=headers, json={
        "supplier_id": sup_id,
        "items": [{"product_id": prod_id, "quantity": "5", "unit_cost": "100.00"}],
        "payment_method": "cash",
        "paid_amount": "500.00"
    })
    assert pur1_res.status_code == 201

    # --- 5. Credit Purchase: 5 units @ ₹100 = ₹500, ₹0 paid ---
    # MUST NOT create cash outflow!
    pur2_res = client.post("/api/v1/purchases", headers=headers, json={
        "supplier_id": sup_id,
        "items": [{"product_id": prod_id, "quantity": "5", "unit_cost": "100.00"}],
        "payment_method": "credit",
        "paid_amount": "0.00"
    })
    assert pur2_res.status_code == 201

    # --- 6. Supplier AP Payment: ₹250 via Bank Transfer ---
    # Enters cashbook now!
    sup_pay = client.post(f"/api/v1/suppliers/{sup_id}/payments", headers=headers, json={
        "amount": "250.00",
        "payment_mode": "bank_transfer",
        "notes": "Oil Mills advance settlement"
    })
    assert sup_pay.status_code == 201

    # --- 7. Operating Expense: Rent ₹150 paid in Cash ---
    cats_res = client.get("/api/v1/expense-categories", headers=headers).json()["data"]
    rent_cat = next(c for c in cats_res if c["name"] == "Rent")

    exp_res = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": rent_cat["id"],
        "amount": "150.00",
        "payment_method": "cash",
        "payment_status": "paid",
        "description": "Daily godown charge"
    })
    assert exp_res.status_code == 201

    # --- 8. Unpaid Expense: ₹400 (MUST NOT enter cashbook!) ---
    exp_unpaid = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": rent_cat["id"],
        "amount": "400.00",
        "payment_method": "cash",
        "payment_status": "unpaid",
        "description": "Pending bill"
    })
    assert exp_unpaid.status_code == 201

    # --- 9. Check Cashbook Totals Reconciliation ---
    # Expected Inflows: ₹300 (Sale 1) + ₹200 (Khata) = ₹500
    # Expected Outflows: ₹500 (Purchase 1) + ₹250 (Supplier AP) + ₹150 (Rent Expense) = ₹900
    # Net Movement: 500 - 900 = -400
    summary = client.get("/api/v1/cashbook/summary", headers=headers).json()["data"]
    assert Decimal(summary["total_inflows"]) == Decimal("500.0000")
    assert Decimal(summary["total_outflows"]) == Decimal("900.0000")
    assert Decimal(summary["net_cash_movement"]) == Decimal("-400.0000")

    # Inflows by mode: cash = 300, upi = 200
    assert Decimal(summary["inflows_by_mode"]["cash"]) == Decimal("300.0000")
    assert Decimal(summary["inflows_by_mode"]["upi"]) == Decimal("200.0000")

    # Outflows by mode: cash = 500 + 150 = 650, bank_transfer = 250
    assert Decimal(summary["outflows_by_mode"]["cash"]) == Decimal("650.0000")
    assert Decimal(summary["outflows_by_mode"]["bank_transfer"]) == Decimal("250.0000")

    # Transactions List Verification
    txs_res = client.get("/api/v1/cashbook/transactions", headers=headers)
    assert txs_res.status_code == 200
    txs = txs_res.json()["data"]
    assert len(txs) == 5  # Exactly 5 transactions, no double-counting!
    source_types = [t["source_type"] for t in txs]
    assert "sale_payment" in source_types
    assert "customer_settlement" in source_types
    assert "purchase_payment" in source_types
    assert "supplier_settlement" in source_types
    assert "operating_expense" in source_types


# ============================================================================
# 6. SPLIT PAYMENT CASHBOOK DECOMPOSITION
# ============================================================================

def test_cashbook_split_payment_decomposition(client: TestClient):
    auth = register_user(client, "9876541007", "Split Payment Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Wheat Flour 5kg", "200.00", "280.00", "50")

    # Sale with split payment: ₹100 Cash + ₹180 UPI = ₹280 Total
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "1", "unit_price": "280.00"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "100.00"},
            {"mode": "upi", "amount": "180.00"}
        ],
        "paid_amount": "280.00"
    })
    assert sale_res.status_code == 201

    # Cashbook transactions query
    txs = client.get("/api/v1/cashbook/transactions", headers=headers).json()["data"]
    assert len(txs) == 2  # Decomposed cleanly into 2 entries
    modes = {t["payment_mode"]: Decimal(t["amount"]) for t in txs}
    assert modes["cash"] == Decimal("100.0000")
    assert modes["upi"] == Decimal("180.0000")

    summary = client.get("/api/v1/cashbook/summary", headers=headers).json()["data"]
    assert Decimal(summary["total_inflows"]) == Decimal("280.0000")
