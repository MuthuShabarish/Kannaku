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
# 1. EMPTY PERIOD & DATE FILTERING
# ============================================================================

def test_reports_empty_period_returns_zeros(client: TestClient):
    auth = register_user(client, "9876540001", "Empty Store")
    headers = auth["headers"]

    res = client.get("/api/v1/reports/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert Decimal(data["sales"]["total_revenue"]) == Decimal("0.0000")
    assert data["sales"]["invoice_count"] == 0
    assert Decimal(data["purchases"]["total_purchases"]) == Decimal("0.0000")
    assert Decimal(data["expenses"]["total_expenses"]) == Decimal("0.0000")
    assert Decimal(data["profit"]["gross_profit"]) == Decimal("0.0000")
    assert Decimal(data["profit"]["operating_profit_estimate"]) == Decimal("0.0000")
    assert Decimal(data["cash_movement"]["net_cash_movement"]) == Decimal("0.0000")
    assert data["period"]["is_empty_range"] is True


def test_reports_date_filtering_boundaries(client: TestClient):
    auth = register_user(client, "9876540002", "Date Filter Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Rice 1kg", "40.0000", "60.0000", "50.0000")

    # Complete a sale today
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "2.0000"}],
        "payment_method": "cash",
        "paid_amount": "120.0000"
    })
    assert sale_res.status_code == 201

    # Query with past date range (should be empty)
    res_past = client.get(
        "/api/v1/reports/summary?start_date=2020-01-01T00:00:00Z&end_date=2020-01-31T23:59:59Z",
        headers=headers
    )
    assert res_past.status_code == 200
    assert Decimal(res_past.json()["data"]["sales"]["total_revenue"]) == Decimal("0.0000")

    # Query with wide range including today
    res_wide = client.get(
        "/api/v1/reports/summary?start_date=2020-01-01T00:00:00Z&end_date=2030-12-31T23:59:59Z",
        headers=headers
    )
    assert res_wide.status_code == 200
    assert Decimal(res_wide.json()["data"]["sales"]["total_revenue"]) == Decimal("120.0000")
    assert res_wide.json()["data"]["sales"]["invoice_count"] == 1


# ============================================================================
# 2. HISTORICAL COGS SNAPSHOT INTEGRITY & GROSS PROFIT
# ============================================================================

def test_historical_cogs_snapshot_remains_unchanged_after_cost_change(client: TestClient):
    """
    CRITICAL FINANCIAL SAFEGUARD:
    Historical COGS must never be recalculated from current product cost or current moving average.
    """
    auth = register_user(client, "9876540003", "Snapshot Integrity Store")
    headers = auth["headers"]

    # Product initially costs 50, selling price 100
    prod = create_sample_product(client, headers, "Wheat Flour", "50.0000", "100.0000", "20.0000")
    p_id = prod["id"]

    # Sell 2 units -> Revenue = 200, Historical COGS = 100 (2 * 50)
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p_id, "quantity": "2.0000"}],
        "payment_method": "cash",
        "paid_amount": "200.0000"
    })
    assert sale_res.status_code == 201

    # Check report before product cost change
    res_before = client.get("/api/v1/reports/summary", headers=headers)
    assert res_before.status_code == 200
    data_before = res_before.json()["data"]
    assert Decimal(data_before["sales"]["total_revenue"]) == Decimal("200.0000")
    assert Decimal(data_before["profit"]["cogs_total"]) == Decimal("100.0000")
    assert Decimal(data_before["profit"]["gross_profit"]) == Decimal("100.0000")

    # Now change product purchase_cost to 90.0000 (e.g. supplier price inflation)
    upd_res = client.put(f"/api/v1/products/{p_id}", headers=headers, json={
        "purchase_cost": "90.0000"
    })
    assert upd_res.status_code == 200

    # Query report again: Historical COGS MUST still be 100.0000, NOT 180.0000!
    res_after = client.get("/api/v1/reports/summary", headers=headers)
    assert res_after.status_code == 200
    data_after = res_after.json()["data"]
    assert Decimal(data_after["profit"]["cogs_total"]) == Decimal("100.0000"), (
        "Historical COGS must remain locked to snapshot, not recalculated from new product cost"
    )
    assert Decimal(data_after["profit"]["gross_profit"]) == Decimal("100.0000")


# ============================================================================
# 3. PURCHASES NOT DOUBLE COUNTED & EXPENSE STATUS HANDLING
# ============================================================================

def test_purchases_not_treated_as_operating_expenses_and_expense_status(client: TestClient):
    auth = register_user(client, "9876540004", "No Double Counting Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Tea Box", "30.0000", "50.0000", "10.0000")

    # 1. Record an inventory purchase of 500 (affecting stock and accounts payable/cash, NOT operating expenses)
    pur_res = client.post("/api/v1/purchases", headers=headers, json={
        "invoice_number": "SUP-INV-001",
        "items": [{
            "product_id": prod["id"],
            "quantity": "10.0000",
            "unit_cost": "30.0000"
        }],
        "payment_method": "cash",
        "paid_amount": "300.0000"
    })
    assert pur_res.status_code == 201

    # 2. Get default expense categories
    cats_res = client.get("/api/v1/expense-categories", headers=headers)
    cat_id = cats_res.json()["data"][0]["id"]

    # 3. Record a Paid Operating Expense of 150 (Rent/Tea)
    exp_paid = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": cat_id,
        "amount": "150.0000",
        "payment_method": "cash",
        "payment_status": "paid",
        "description": "Office tea and snacks"
    })
    assert exp_paid.status_code == 201

    # 4. Record an Unpaid Operating Expense of 200 (Accrued EB bill)
    exp_unpaid = client.post("/api/v1/expenses", headers=headers, json={
        "category_id": cat_id,
        "amount": "200.0000",
        "payment_method": "bank_transfer",
        "payment_status": "unpaid",
        "description": "Electricity EB bill pending"
    })
    assert exp_unpaid.status_code == 201

    # 5. Check reports
    rep_res = client.get("/api/v1/reports/summary", headers=headers)
    assert rep_res.status_code == 200
    data = rep_res.json()["data"]

    # Purchases must show 300
    assert Decimal(data["purchases"]["total_purchases"]) == Decimal("300.0000")

    # Operating expenses must show active expenses (paid 150 + unpaid 200 = 350)
    # MUST NOT include the 300 inventory purchase!
    assert Decimal(data["expenses"]["total_expenses"]) == Decimal("350.0000")
    assert Decimal(data["expenses"]["paid_expenses"]) == Decimal("150.0000")
    assert Decimal(data["expenses"]["unpaid_expenses"]) == Decimal("200.0000")

    # Operating profit estimate rule: Gross profit (0) - Paid expenses (150) = -150
    assert Decimal(data["profit"]["operating_expenses"]) == Decimal("150.0000")
    assert Decimal(data["profit"]["operating_profit_estimate"]) == Decimal("-150.0000")


# ============================================================================
# 4. SPLIT PAYMENTS & KHATA COLLECTIONS REVENUE SAFEGUARDS
# ============================================================================

def test_split_payments_and_khata_do_not_duplicate_revenue(client: TestClient):
    auth = register_user(client, "9876540005", "Revenue Safeguard Store")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Soap", "20.0000", "40.0000", "100.0000")

    # Customer
    cust_res = client.post("/api/v1/customers", headers=headers, json={
        "name": "Anbu Selvan",
        "phone": "9443100001",
        "credit_limit": "5000.0000"
    })
    cust_id = cust_res.json()["data"]["id"]

    # 1. Sale with Split Payment: 2 soaps (Total 80) -> Paid 30 cash + 50 upi
    sale_split = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "2.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "30.0000"},
            {"mode": "upi", "amount": "50.0000"}
        ]
    })
    assert sale_split.status_code == 201

    # Revenue should be 80, NOT 160 (split must not multiply revenue)
    rep1 = client.get("/api/v1/reports/summary", headers=headers).json()["data"]
    assert Decimal(rep1["sales"]["total_revenue"]) == Decimal("80.0000")
    assert rep1["sales"]["invoice_count"] == 1

    # 2. Credit Sale of 100 to customer Anbu (unpaid)
    sale_credit = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust_id,
        "items": [{"product_id": prod["id"], "quantity": "2.5000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })
    assert sale_credit.status_code == 201  # 2.5 * 40 = 100

    # Total revenue is now 80 + 100 = 180
    rep2 = client.get("/api/v1/reports/summary", headers=headers).json()["data"]
    assert Decimal(rep2["sales"]["total_revenue"]) == Decimal("180.0000")

    # 3. Customer pays 100 to settle Khata balance
    khata_pay = client.post(f"/api/v1/customers/{cust_id}/payments", headers=headers, json={
        "amount": "100.0000",
        "payment_mode": "cash",
        "notes": "Debt settlement"
    })
    assert khata_pay.status_code == 201

    # Sales revenue MUST STILL be 180 (Khata collection is cash liquidity, NOT new revenue!)
    rep3 = client.get("/api/v1/reports/summary", headers=headers).json()["data"]
    assert Decimal(rep3["sales"]["total_revenue"]) == Decimal("180.0000")

    # But cashbook inflows include: 80 (split sale) + 100 (Khata collection) = 180
    assert Decimal(rep3["cash_movement"]["total_inflows"]) == Decimal("180.0000")


# ============================================================================
# 5. SALES TRENDS, PRODUCT PERFORMANCE & PROFIT OVERVIEW
# ============================================================================

def test_sales_trends_and_product_sales_reports(client: TestClient):
    auth = register_user(client, "9876540006", "Analytics Store")
    headers = auth["headers"]

    p1 = create_sample_product(client, headers, "Pen Blue", "5.0000", "10.0000", "100.0000")
    p2 = create_sample_product(client, headers, "Notebook 200p", "30.0000", "50.0000", "50.0000")

    # Sell 10 pens (Rev: 100, COGS: 50) and 2 notebooks (Rev: 100, COGS: 60)
    s1 = client.post("/api/v1/sales", headers=headers, json={
        "items": [
            {"product_id": p1["id"], "quantity": "10.0000"},
            {"product_id": p2["id"], "quantity": "2.0000"}
        ],
        "payment_method": "cash",
        "paid_amount": "200.0000"
    })
    assert s1.status_code == 201

    # 1. Test Sales Trends
    trends_res = client.get("/api/v1/reports/sales-trends?interval=day", headers=headers)
    assert trends_res.status_code == 200
    t_data = trends_res.json()["data"]
    assert len(t_data["trends"]) >= 1
    assert Decimal(t_data["trends"][0]["sales_revenue"]) == Decimal("200.0000")
    assert Decimal(t_data["trends"][0]["cogs_total"]) == Decimal("110.0000")
    assert Decimal(t_data["trends"][0]["gross_profit"]) == Decimal("90.0000")

    # 2. Test Product Sales Performance
    prod_res = client.get("/api/v1/reports/product-sales?limit=5", headers=headers)
    assert prod_res.status_code == 200
    p_data = prod_res.json()["data"]
    assert len(p_data["top_by_revenue"]) == 2
    # Pen quantity = 10, Notebook quantity = 2
    top_qty = p_data["top_by_quantity"]
    assert top_qty[0]["product_name"] == "Pen Blue"
    assert Decimal(top_qty[0]["quantity_sold"]) == Decimal("10.0000")

    # 3. Test Profit Overview Endpoint
    profit_res = client.get("/api/v1/reports/profit-overview", headers=headers)
    assert profit_res.status_code == 200
    prof_data = profit_res.json()["data"]
    assert Decimal(prof_data["profit"]["gross_profit"]) == Decimal("90.0000")
    assert "sales_revenue" in prof_data["accounting_rules"]
    assert "cogs" in prof_data["accounting_rules"]


# ============================================================================
# 6. TENANT ISOLATION
# ============================================================================

def test_reports_strict_tenant_isolation(client: TestClient):
    auth_a = register_user(client, "9876540007", "Tenant Alpha")
    auth_b = register_user(client, "9876540008", "Tenant Beta")

    # Tenant A generates 500 in sales
    p_a = create_sample_product(client, auth_a["headers"], "Alpha Item", "10.0000", "50.0000", "20.0000")
    client.post("/api/v1/sales", headers=auth_a["headers"], json={
        "items": [{"product_id": p_a["id"], "quantity": "10.0000"}],
        "payment_method": "cash",
        "paid_amount": "500.0000"
    })

    # Tenant A sees 500
    res_a = client.get("/api/v1/reports/summary", headers=auth_a["headers"])
    assert Decimal(res_a.json()["data"]["sales"]["total_revenue"]) == Decimal("500.0000")

    # Tenant B must see 0! Strict isolation
    res_b = client.get("/api/v1/reports/summary", headers=auth_b["headers"])
    assert Decimal(res_b.json()["data"]["sales"]["total_revenue"]) == Decimal("0.0000")
