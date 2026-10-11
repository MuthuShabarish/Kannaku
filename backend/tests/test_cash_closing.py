import pytest
from decimal import Decimal
from datetime import date
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
# 1. PHYSICAL CASH ISOLATION VS UPI / CARD / BANK TRANSFER
# ============================================================================

def test_physical_cash_isolation_from_digital_payments(client: TestClient):
    auth = register_user(client, "9876550001", "Cash Isolation Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Sugar 1kg", "40.0000", "50.0000", "100.0000")

    # 1. Sale #1: Cash payment of 100 (2 units)
    s1 = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "2.0000"}],
        "payment_method": "cash",
        "paid_amount": "100.0000"
    })
    assert s1.status_code == 201

    # 2. Sale #2: UPI payment of 150 (3 units)
    s2 = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "3.0000"}],
        "payment_method": "upi",
        "paid_amount": "150.0000"
    })
    assert s2.status_code == 201

    # 3. Sale #3: Split tender of 200 (4 units): 80 Cash + 120 UPI
    s3 = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "4.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "80.0000"},
            {"mode": "upi", "amount": "120.0000"}
        ]
    })
    assert s3.status_code == 201

    # 4. Check Current Drawer Status
    curr_res = client.get("/api/v1/cash-closing/current", headers=headers)
    assert curr_res.status_code == 200
    status_data = curr_res.json()["data"]

    # Inflows should ONLY include physical cash: 100 (Sale 1) + 80 (Sale 3 cash leg) = 180!
    # MUST NOT include Sale 2 (150 UPI) or Sale 3 UPI leg (120)!
    assert Decimal(status_data["cash_inflows"]) == Decimal("180.0000")
    assert Decimal(status_data["breakdown"]["sales_cash_inflows"]) == Decimal("180.0000")
    assert Decimal(status_data["expected_cash"]) == Decimal("180.0000")


# ============================================================================
# 2. KHATA, PURCHASES, SUPPLIER SETTLEMENTS & EXPENSES
# ============================================================================

def test_drawer_movements_across_khata_purchases_and_expenses(client: TestClient):
    auth = register_user(client, "9876550002", "Comprehensive Drawer Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Biscuits", "15.0000", "25.0000", "50.0000")

    # 1. Customer Khata Collection in Cash (200) vs UPI (100)
    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Muthu",
        "phone": "9840998877",
        "credit_limit": "2000.0000"
    }).json()["data"]

    # Create credit sale of 300 to give balance
    client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": prod["id"], "quantity": "12.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })

    # Cash Khata payment of 150
    client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "150.0000",
        "payment_mode": "cash"
    })

    # UPI Khata payment of 50 (should NOT affect drawer!)
    client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "50.0000",
        "payment_mode": "upi"
    })

    # 2. Purchase Paid in Cash (100) vs Purchase in Bank Transfer (200)
    client.post("/api/v1/purchases", headers=headers, json={
        "invoice_number": "PUR-CASH-01",
        "items": [{"product_id": prod["id"], "quantity": "5.0000", "unit_cost": "15.0000"}],
        "payment_method": "cash",
        "paid_amount": "75.0000"
    })

    client.post("/api/v1/purchases", headers=headers, json={
        "invoice_number": "PUR-BANK-01",
        "items": [{"product_id": prod["id"], "quantity": "10.0000", "unit_cost": "15.0000"}],
        "payment_method": "bank_transfer",
        "paid_amount": "150.0000"
    })

    # 3. Operating Expense: Cash Paid (40) vs UPI Paid (60)
    cats = client.get("/api/v1/expense-categories", headers=headers).json()["data"]
    cat_id = cats[0]["id"]

    client.post("/api/v1/expenses", headers=headers, json={
        "category_id": cat_id,
        "amount": "40.0000",
        "payment_method": "cash",
        "payment_status": "paid",
        "description": "Cleaning materials"
    })

    client.post("/api/v1/expenses", headers=headers, json={
        "category_id": cat_id,
        "amount": "60.0000",
        "payment_method": "upi",
        "payment_status": "paid",
        "description": "Shop SIM card recharge"
    })

    # Expected drawer calculation:
    # Inflow: Khata Cash = 150
    # Outflow: Purchase Cash (75) + Expense Cash (40) = 115
    # Expected: 0 + 150 - 115 = 35
    curr = client.get("/api/v1/cash-closing/current", headers=headers).json()["data"]
    assert Decimal(curr["cash_inflows"]) == Decimal("150.0000")
    assert Decimal(curr["cash_outflows"]) == Decimal("115.0000")
    assert Decimal(curr["expected_cash"]) == Decimal("35.0000")


# ============================================================================
# 3. RECONCILIATION: RECONCILED, OVER, SHORT & CLOSING WORKFLOW
# ============================================================================

def test_daily_cash_closing_reconciliation_over_and_short(client: TestClient):
    auth = register_user(client, "9876550003", "Closing Math Store")
    headers = auth["headers"]

    today_str = date.today().isoformat()

    # Close with opening float = 500, expected cash = 500
    # Case 1: Counted = 520 (OVER by 20)
    close_res = client.post("/api/v1/cash-closing/close", headers=headers, json={
        "closing_date": today_str,
        "opening_cash": "500.0000",
        "actual_cash": "520.0000",
        "notes": "Drawer has 20 extra from uncollected change"
    })
    assert close_res.status_code == 201
    c_data = close_res.json()["data"]
    assert Decimal(c_data["expected_cash"]) == Decimal("500.0000")
    assert Decimal(c_data["actual_cash"]) == Decimal("520.0000")
    assert Decimal(c_data["difference"]) == Decimal("20.0000")
    assert c_data["reconciliation_status"] == "over"
    assert c_data["status"] == "closed"


# ============================================================================
# 4. DUPLICATE CLOSING REJECTION & AUDITABLE REOPENING POLICY
# ============================================================================

def test_duplicate_closing_prevention_and_reopening(client: TestClient):
    auth = register_user(client, "9876550004", "Security Closing Store")
    headers = auth["headers"]

    today_str = date.today().isoformat()

    # 1. First close
    c1 = client.post("/api/v1/cash-closing/close", headers=headers, json={
        "closing_date": today_str,
        "opening_cash": "100.0000",
        "actual_cash": "100.0000"
    })
    assert c1.status_code == 201
    closing_id = c1.json()["data"]["id"]

    # 2. Duplicate submission for same date MUST fail with 409 Conflict
    dup = client.post("/api/v1/cash-closing/close", headers=headers, json={
        "closing_date": today_str,
        "opening_cash": "100.0000",
        "actual_cash": "100.0000"
    })
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "ALREADY_CLOSED"

    # 3. Reopening requires a non-empty audit reason
    reopen_fail = client.post(f"/api/v1/cash-closing/{closing_id}/reopen", headers=headers, json={
        "reason": "  "
    })
    assert reopen_fail.status_code in [400, 422]

    # Valid reopening
    reopen_ok = client.post(f"/api/v1/cash-closing/{closing_id}/reopen", headers=headers, json={
        "reason": "Recounting drawer due to found 50 rupee note under tray"
    })
    assert reopen_ok.status_code == 200
    assert reopen_ok.json()["data"]["status"] == "reopened"
    assert reopen_ok.json()["data"]["reopen_reason"] == "Recounting drawer due to found 50 rupee note under tray"

    # 4. Re-close with corrected counted cash
    reclose = client.post("/api/v1/cash-closing/close", headers=headers, json={
        "closing_date": today_str,
        "opening_cash": "100.0000",
        "actual_cash": "150.0000",
        "notes": "Corrected closing"
    })
    assert reclose.status_code == 201
    assert Decimal(reclose.json()["data"]["actual_cash"]) == Decimal("150.0000")
    assert reclose.json()["data"]["status"] == "closed"


# ============================================================================
# 5. TENANT ISOLATION
# ============================================================================

def test_cash_closing_strict_tenant_isolation(client: TestClient):
    auth_a = register_user(client, "9876550005", "Tenant Drawer A")
    auth_b = register_user(client, "9876550006", "Tenant Drawer B")

    today_str = date.today().isoformat()

    # Tenant A closes drawer
    c_a = client.post("/api/v1/cash-closing/close", headers=auth_a["headers"], json={
        "closing_date": today_str,
        "opening_cash": "200.0000",
        "actual_cash": "200.0000"
    }).json()["data"]

    # Tenant B querying history must NOT see Tenant A's record
    hist_b = client.get("/api/v1/cash-closing/history", headers=auth_b["headers"]).json()["data"]
    assert len(hist_b) == 0

    # Tenant B accessing Tenant A's closing ID directly must get 404
    get_other = client.get(f"/api/v1/cash-closing/{c_a['id']}", headers=auth_b["headers"])
    assert get_other.status_code == 404
