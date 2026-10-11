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
# CUSTOMER & KHATA LEDGER TESTS
# ============================================================================

def test_customer_crud_and_duplicate_phone_rejection(client: TestClient):
    auth = register_user(client, "9876520001", "Murugan Stores")
    headers = auth["headers"]

    # 1. Create Customer
    res = client.post("/api/v1/customers", headers=headers, json={
        "name": "Karthik Raja",
        "phone": "9840123456",
        "email": "karthik@example.com",
        "address": "12 Anna Salai, Chennai",
        "credit_limit": "5000.0000"
    })
    assert res.status_code == 201
    cust = res.json()["data"]
    assert cust["name"] == "Karthik Raja"
    assert cust["phone"] == "9840123456"
    assert cust["current_balance"] == "0.0000"
    cust_id = cust["id"]

    # 2. Reject duplicate phone within same business
    dup_res = client.post("/api/v1/customers", headers=headers, json={
        "name": "Karthik R",
        "phone": "98401-23456",  # cleaned phone match
        "credit_limit": "2000.0000"
    })
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CUSTOMER_PHONE_EXISTS"

    # 3. List customers
    list_res = client.get("/api/v1/customers?search=karthik", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1

    # 4. Update customer
    up_res = client.put(f"/api/v1/customers/{cust_id}", headers=headers, json={
        "credit_limit": "8000.0000",
        "address": "45 Trichy Road, Coimbatore"
    })
    assert up_res.status_code == 200
    assert Decimal(up_res.json()["data"]["credit_limit"]) == Decimal("8000.0000")


def test_customer_khata_payment_settlement(client: TestClient):
    auth = register_user(client, "9876520002", "Annamalai Traders")
    headers = auth["headers"]

    # Create customer with credit limit
    cust_res = client.post("/api/v1/customers", headers=headers, json={
        "name": "Senthil Nathan",
        "phone": "9840234567",
        "credit_limit": "10000.0000"
    })
    cust_id = cust_res.json()["data"]["id"]

    # Create product with stock
    prod = create_sample_product(client, headers, "Cooking Oil 1L", "120.0000", "150.0000", "20.0000")

    # Make Credit Sale of 2 units (Total = 300)
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust_id,
        "items": [{"product_id": prod["id"], "quantity": "2.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })
    assert sale_res.status_code == 201
    assert sale_res.json()["data"]["credit_amount"] == "300.0000"
    assert sale_res.json()["data"]["payment_status"] == "unpaid"

    # Verify customer balance increased to 300
    detail_res = client.get(f"/api/v1/customers/{cust_id}", headers=headers)
    assert detail_res.status_code == 200
    assert Decimal(detail_res.json()["data"]["current_balance"]) == Decimal("300.0000")
    assert len(detail_res.json()["data"]["recent_entries"]) == 1
    assert detail_res.json()["data"]["recent_entries"][0]["entry_type"] == "credit_sale"

    # Customer pays 200 towards debt
    pay_res = client.post(f"/api/v1/customers/{cust_id}/payments", headers=headers, json={
        "amount": "200.0000",
        "payment_mode": "cash",
        "notes": "Partial settlement"
    })
    assert pay_res.status_code == 201
    assert Decimal(pay_res.json()["data"]["balance_after"]) == Decimal("100.0000")

    # Verify updated customer balance is now 100
    updated_cust = client.get(f"/api/v1/customers/{cust_id}", headers=headers).json()["data"]
    assert Decimal(updated_cust["current_balance"]) == Decimal("100.0000")
    assert len(updated_cust["recent_entries"]) == 2


# ============================================================================
# POS CHECKOUT & PAYMENT METHOD TESTS
# ============================================================================

def test_successful_cash_sale_with_stock_deduction_and_cogs(client: TestClient):
    auth = register_user(client, "9876520003", "Kovai Provision")
    headers = auth["headers"]

    # Create products:
    # Prod 1: Cost 40, Selling 50, Stock 100
    # Prod 2: Cost 80, Selling 100, Stock 50
    p1 = create_sample_product(client, headers, "Basmati Rice 1kg", "40.0000", "50.0000", "100.0000")
    p2 = create_sample_product(client, headers, "Ghee 500ml", "80.0000", "100.0000", "50.0000")

    # Execute Sale:
    # 2x Basmati Rice (2 * 50 = 100, line discount 5 = 95)
    # 1x Ghee (1 * 100 = 100, line discount 0 = 100)
    # Subtotal = 195, overall discount = 15, Total = 180
    checkout_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [
            {"product_id": p1["id"], "quantity": "2.0000", "discount_amount": "5.0000"},
            {"product_id": p2["id"], "quantity": "1.0000", "discount_amount": "0.0000"}
        ],
        "discount_amount": "15.0000",
        "payment_method": "cash",
        "notes": "Walk-in cash customer"
    })
    assert checkout_res.status_code == 201, checkout_res.text
    sale = checkout_res.json()["data"]

    assert sale["invoice_number"].startswith("INV-")
    assert Decimal(sale["subtotal_amount"]) == Decimal("195.0000")
    assert Decimal(sale["discount_amount"]) == Decimal("15.0000")
    assert Decimal(sale["total_amount"]) == Decimal("180.0000")
    assert Decimal(sale["paid_amount"]) == Decimal("180.0000")
    assert Decimal(sale["credit_amount"]) == Decimal("0.0000")
    assert sale["payment_status"] == "paid"

    # Check COGS: (2 * 40) + (1 * 80) = 160
    assert Decimal(sale["cogs_total"]) == Decimal("160.0000")

    # Verify line items snapshots
    assert len(sale["items"]) == 2
    item1 = next(it for it in sale["items"] if it["product_id"] == p1["id"])
    assert item1["product_name"] == "Basmati Rice 1kg"
    assert Decimal(item1["unit_price"]) == Decimal("50.0000")
    assert Decimal(item1["unit_cost"]) == Decimal("40.0000")
    assert Decimal(item1["line_cogs"]) == Decimal("80.0000")

    # Verify inventory balance deducted
    p1_stock = client.get(f"/api/v1/products/{p1['id']}", headers=headers).json()["data"]["current_stock"]
    p2_stock = client.get(f"/api/v1/products/{p2['id']}", headers=headers).json()["data"]["current_stock"]
    assert Decimal(p1_stock) == Decimal("98.0000")
    assert Decimal(p2_stock) == Decimal("49.0000")

    # Verify StockMovement records
    mov_res = client.get(f"/api/v1/inventory/movements?product_id={p1['id']}", headers=headers)
    assert mov_res.status_code == 200
    movements = mov_res.json()["data"]
    sale_mov = next(m for m in movements if m["movement_type"] == "sale")
    assert Decimal(sale_mov["quantity_delta"]) == Decimal("-2.0000")
    assert Decimal(sale_mov["balance_after"]) == Decimal("98.0000")


def test_upi_and_card_checkout(client: TestClient):
    auth = register_user(client, "9876520004", "Velan Supermarket")
    headers = auth["headers"]

    p = create_sample_product(client, headers, "Tea Powder 250g", "60.0000", "75.0000", "20.0000")

    # UPI checkout
    upi_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "upi",
        "notes": "GooglePay ref 12345"
    })
    assert upi_res.status_code == 201
    assert upi_res.json()["data"]["payment_method"] == "upi"
    assert upi_res.json()["data"]["payment_status"] == "paid"
    assert upi_res.json()["data"]["payments"][0]["payment_mode"] == "upi"

    # Card checkout
    card_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "card",
        "notes": "Visa POS swipe"
    })
    assert card_res.status_code == 201
    assert card_res.json()["data"]["payment_method"] == "card"
    assert card_res.json()["data"]["payment_status"] == "paid"
    assert card_res.json()["data"]["payments"][0]["payment_mode"] == "card"


def test_split_payment_checkout(client: TestClient):
    auth = register_user(client, "9876520005", "Madurai Textiles")
    headers = auth["headers"]

    p = create_sample_product(client, headers, "Cotton Dhoti", "200.0000", "300.0000", "15.0000")

    # Buy 2 dhotis = 600. Split: 400 Cash + 200 UPI
    split_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "400.0000"},
            {"mode": "upi", "amount": "200.0000"}
        ]
    })
    assert split_res.status_code == 201
    sale = split_res.json()["data"]
    assert Decimal(sale["total_amount"]) == Decimal("600.0000")
    assert Decimal(sale["paid_amount"]) == Decimal("600.0000")
    assert sale["payment_status"] == "paid"
    assert len(sale["payments"]) == 2

    # Split payment overpaying total should be rejected
    bad_split = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "200.0000"},
            {"mode": "upi", "amount": "200.0000"}
        ]  # Total is 300, split is 400
    })
    assert bad_split.status_code == 400
    assert bad_split.json()["error"]["code"] == "OVERPAID"


def test_credit_limit_exceeded_rejection(client: TestClient):
    auth = register_user(client, "9876520006", "Salem Stores")
    headers = auth["headers"]

    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Manickam",
        "phone": "9840333444",
        "credit_limit": "500.0000"
    }).json()["data"]

    p = create_sample_product(client, headers, "Silk Saree", "500.0000", "800.0000", "10.0000")

    # Attempt credit sale of 800 which exceeds limit of 500
    res = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CREDIT_LIMIT_EXCEEDED"


# ============================================================================
# VALIDATION, ATOMIC ROLLBACK & IDEMPOTENCY TESTS
# ============================================================================

def test_insufficient_stock_rejection_and_atomic_rollback(client: TestClient):
    auth = register_user(client, "9876520007", "Thanjavur Mart")
    headers = auth["headers"]

    # Stock is only 3
    p = create_sample_product(client, headers, "Filter Coffee 500g", "150.0000", "200.0000", "3.0000")

    # Attempt to buy 5
    res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "5.0000"}],
        "payment_method": "cash"
    })
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Confirm stock was untouched (still 3)
    stock_after = client.get(f"/api/v1/products/{p['id']}", headers=headers).json()["data"]["current_stock"]
    assert Decimal(stock_after) == Decimal("3.0000")

    # Confirm no sales record was created
    sales_list = client.get("/api/v1/sales", headers=headers).json()["data"]
    assert len(sales_list) == 0


def test_idempotency_key_duplicate_prevention(client: TestClient):
    auth = register_user(client, "9876520008", "Idempotent Mart")
    headers = auth["headers"]

    p = create_sample_product(client, headers, "Soap 100g", "25.0000", "35.0000", "50.0000")

    idempotency_key = "uniq-req-pos-12345"

    payload = {
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "cash",
        "idempotency_key": idempotency_key
    }

    # 1. First checkout attempt
    res1 = client.post("/api/v1/sales", headers=headers, json=payload)
    assert res1.status_code == 201
    sale1 = res1.json()["data"]

    # Stock reduced from 50 to 48
    stock1 = client.get(f"/api/v1/products/{p['id']}", headers=headers).json()["data"]["current_stock"]
    assert Decimal(stock1) == Decimal("48.0000")

    # 2. Second checkout attempt with identical idempotency_key (simulating network retry)
    res2 = client.post("/api/v1/sales", headers=headers, json=payload)
    assert res2.status_code == 201
    sale2 = res2.json()["data"]

    # Same invoice returned, no duplicate sale
    assert sale1["id"] == sale2["id"]
    assert sale1["invoice_number"] == sale2["invoice_number"]

    # Stock is STILL 48, NOT 46!
    stock2 = client.get(f"/api/v1/products/{p['id']}", headers=headers).json()["data"]["current_stock"]
    assert Decimal(stock2) == Decimal("48.0000")


def test_historical_invoice_integrity_after_product_updates(client: TestClient):
    auth = register_user(client, "9876520009", "Archive Store")
    headers = auth["headers"]

    # Create product: Price 100, Cost 60
    p = create_sample_product(client, headers, "Sugar 1kg", "60.0000", "100.0000", "30.0000")

    # Complete Sale
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "cash"
    })
    assert sale_res.status_code == 201
    sale_id = sale_res.json()["data"]["id"]

    # Now edit product: Rename product, increase price to 150, cost to 90
    up_res = client.put(f"/api/v1/products/{p['id']}", headers=headers, json={
        "name": "Super Refined Sugar 1kg",
        "selling_price": "150.0000",
        "purchase_cost": "90.0000"
    })
    assert up_res.status_code == 200

    # Query completed sale details
    invoice = client.get(f"/api/v1/sales/{sale_id}", headers=headers).json()["data"]

    # Historical invoice must retain original name, original price (100) and original COGS (60)
    assert invoice["items"][0]["product_name"] == "Sugar 1kg"
    assert Decimal(invoice["items"][0]["unit_price"]) == Decimal("100.0000")
    assert Decimal(invoice["items"][0]["unit_cost"]) == Decimal("60.0000")
    assert Decimal(invoice["total_amount"]) == Decimal("200.0000")


def test_cross_tenant_sales_access_isolation(client: TestClient):
    auth_a = register_user(client, "9876520010", "Tenant A Shop")
    auth_b = register_user(client, "9876520011", "Tenant B Shop")

    p = create_sample_product(client, auth_a["headers"], "Tenant A Item", "10.0000", "20.0000", "10.0000")

    # Complete sale in Tenant A
    sale_a = client.post("/api/v1/sales", headers=auth_a["headers"], json={
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "cash"
    }).json()["data"]

    # Tenant B attempts to fetch Tenant A's sale
    res_b = client.get(f"/api/v1/sales/{sale_a['id']}", headers=auth_b["headers"])
    assert res_b.status_code == 404


def test_sales_overview_metrics(client: TestClient):
    auth = register_user(client, "9876520012", "Metrics Enterprise")
    headers = auth["headers"]

    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Regular Customer",
        "phone": "9840999888",
        "credit_limit": "2000.0000"
    }).json()["data"]

    p = create_sample_product(client, headers, "Gadget", "50.0000", "100.0000", "20.0000")

    # Sale 1: Cash 100
    client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "cash"
    })

    # Sale 2: Credit 200
    client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })

    # Fetch overview
    ov = client.get("/api/v1/sales/overview", headers=headers).json()["data"]
    assert ov["total_sales_count"] == 2
    assert Decimal(ov["total_sales_amount"]) == Decimal("300.0000")
    assert Decimal(ov["total_paid_amount"]) == Decimal("100.0000")
    assert Decimal(ov["total_credit_amount"]) == Decimal("200.0000")
    assert Decimal(ov["total_cogs"]) == Decimal("150.0000")  # (1*50) + (2*50)
    assert ov["total_customers"] == 1
    assert Decimal(ov["total_receivable"]) == Decimal("200.0000")


# ============================================================================
# STAGE 4 ACCOUNTING INTEGRITY AUDIT TESTS
# ============================================================================

def test_payment_reconciliation_exact_equation(client: TestClient):
    """
    Audits:
    1. For every sale, total_amount == paid_amount + credit_amount.
    2. Split payment allocations equal paid_amount exactly.
    3. Partial payment produces exact customer credit balance.
    4. Overpayment and invalid allocation rejection.
    """
    auth = register_user(client, "9876530001", "Reconciliation Shop")
    headers = auth["headers"]

    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Audit Customer",
        "phone": "9840888777",
        "credit_limit": "5000.0000"
    }).json()["data"]

    p = create_sample_product(client, headers, "Wheat Flour 10kg", "350.0000", "450.0000", "50.0000")

    # 1. Split payment checkout: 2 bags = 900.0000. Pay 300 Cash + 400 UPI + 200 Credit
    split_res = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "300.0000"},
            {"mode": "upi", "amount": "400.0000"}
        ]
    })
    assert split_res.status_code == 201
    sale = split_res.json()["data"]

    # Verify Equation: total_amount = paid_amount + credit_amount
    total = Decimal(sale["total_amount"])
    paid = Decimal(sale["paid_amount"])
    credit = Decimal(sale["credit_amount"])
    assert total == Decimal("900.0000")
    assert paid == Decimal("700.0000")
    assert credit == Decimal("200.0000")
    assert total == paid + credit

    # Verify Payments Sum matches paid_amount
    payments_sum = sum(Decimal(pmt["amount"]) for pmt in sale["payments"])
    assert payments_sum == paid
    assert len(sale["payments"]) == 2

    # Verify Customer Khata Balance increased by exactly 200
    cust_after = client.get(f"/api/v1/customers/{cust['id']}", headers=headers).json()["data"]
    assert Decimal(cust_after["current_balance"]) == Decimal("200.0000")

    # 2. Reject split payment exceeding total
    bad_split = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "split",
        "split_payments": [
            {"mode": "cash", "amount": "300.0000"},
            {"mode": "upi", "amount": "300.0000"}
        ]  # Total is 450, split is 600
    })
    assert bad_split.status_code == 400
    assert bad_split.json()["error"]["code"] == "OVERPAID"


def test_settlement_limits_and_inactive_customer_rejected(client: TestClient):
    """
    Audits:
    1. Reject settlements exceeding customer's outstanding debt balance.
    2. Reject settlements when customer has zero debt.
    3. Reject settlements on inactive customers.
    """
    auth = register_user(client, "9876530002", "Settlement Shop")
    headers = auth["headers"]

    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Settlement Tester",
        "phone": "9840777666",
        "credit_limit": "2000.0000"
    }).json()["data"]

    # Customer currently has 0 debt: attempt to pay 100 should be rejected
    no_debt_res = client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "100.0000",
        "payment_mode": "cash"
    })
    assert no_debt_res.status_code == 400
    assert no_debt_res.json()["error"]["code"] == "NO_OUTSTANDING_BALANCE"

    # Now create product and credit sale of 250
    p = create_sample_product(client, headers, "Pulses 1kg", "80.0000", "125.0000", "10.0000")
    client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "2.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })

    # Customer balance is now 250: attempt to settle 300 (exceeding debt) should be rejected
    over_res = client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "300.0000",
        "payment_mode": "cash"
    })
    assert over_res.status_code == 400
    assert over_res.json()["error"]["code"] == "SETTLEMENT_EXCEEDS_BALANCE"

    # Exact settlement of 250 should succeed
    ok_res = client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "250.0000",
        "payment_mode": "cash"
    })
    assert ok_res.status_code == 201
    assert Decimal(ok_res.json()["data"]["balance_after"]) == Decimal("0.0000")

    # Deactivate customer and verify payment rejection
    client.put(f"/api/v1/customers/{cust['id']}", headers=headers, json={"is_active": False})
    inactive_res = client.post(f"/api/v1/customers/{cust['id']}/payments", headers=headers, json={
        "amount": "50.0000",
        "payment_mode": "cash"
    })
    assert inactive_res.status_code == 400
    assert inactive_res.json()["error"]["code"] == "CUSTOMER_INACTIVE"


def test_failed_checkout_leaves_zero_partial_records(client: TestClient):
    """
    Audits:
    When a transaction aborts (e.g. credit limit exceeded), zero partial rows are committed:
    - No Sale row
    - No SaleItem rows
    - No StockMovement rows
    - No Payment rows
    - Customer balance unchanged
    - Product stock unchanged
    """
    auth = register_user(client, "9876530003", "Rollback Verification Shop")
    headers = auth["headers"]

    cust = client.post("/api/v1/customers", headers=headers, json={
        "name": "Limit Customer",
        "phone": "9840666555",
        "credit_limit": "200.0000"
    }).json()["data"]

    p = create_sample_product(client, headers, "Expensive Item", "100.0000", "500.0000", "10.0000")

    # Attempt credit checkout of 500 (exceeds limit 200)
    res = client.post("/api/v1/sales", headers=headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": p["id"], "quantity": "1.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CREDIT_LIMIT_EXCEEDED"

    # Verify no sales exist
    sales = client.get("/api/v1/sales", headers=headers).json()["data"]
    assert len(sales) == 0

    # Verify stock is still 10.0000
    prod_check = client.get(f"/api/v1/products/{p['id']}", headers=headers).json()["data"]
    assert Decimal(prod_check["current_stock"]) == Decimal("10.0000")

    # Verify only opening movement exists, no sale movement
    movs = client.get(f"/api/v1/inventory/movements?product_id={p['id']}", headers=headers).json()["data"]
    assert len(movs) == 1
    assert movs[0]["movement_type"] == "opening"

    # Verify customer balance is still 0.0000
    cust_check = client.get(f"/api/v1/customers/{cust['id']}", headers=headers).json()["data"]
    assert Decimal(cust_check["current_balance"]) == Decimal("0.0000")


def test_moving_average_cogs_exact_reconciliation(client: TestClient):
    """
    Audits Moving Average Costing:
    1. Initial Stock: 10 units @ 100.0000 (Valuation = 1000)
    2. Incoming Adjustment: 10 units @ 200.0000 (Incoming = 2000)
    3. New MAC = (1000 + 2000) / 20 = 150.0000
    4. Sale of 4 units:
       - COGS snapshot in SaleItem = 4 * 150.0000 = 600.0000
       - Unit cost in SaleItem = 150.0000
       - StockMovement unit_cost = 150.0000, quantity_delta = -4.0000, balance_after = 16.0000
    """
    auth = register_user(client, "9876530004", "MAC Accounting Shop")
    headers = auth["headers"]

    p = create_sample_product(client, headers, "MAC Widget", "100.0000", "250.0000", "10.0000")

    # Adjust stock: +10 units at unit cost 200.0000
    adj_res = client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": p["id"],
        "adjustment_type": "increase",
        "quantity": "10.0000",
        "unit_cost": "200.0000",
        "reason": "Batch restock"
    })
    assert adj_res.status_code == 201

    # Execute Sale of 4 units (Price 250, Total 1000)
    sale_res = client.post("/api/v1/sales", headers=headers, json={
        "items": [{"product_id": p["id"], "quantity": "4.0000"}],
        "payment_method": "cash"
    })
    assert sale_res.status_code == 201
    sale = sale_res.json()["data"]

    # Verify MAC snapshot in SaleItem and Sale COGS
    assert Decimal(sale["cogs_total"]) == Decimal("600.0000")
    item = sale["items"][0]
    assert Decimal(item["unit_cost"]) == Decimal("150.0000")
    assert Decimal(item["line_cogs"]) == Decimal("600.0000")
    assert Decimal(item["quantity"]) == Decimal("4.0000")

    # Verify remaining stock is 16
    stock_after = client.get(f"/api/v1/products/{p['id']}", headers=headers).json()["data"]["current_stock"]
    assert Decimal(stock_after) == Decimal("16.0000")

    # Verify StockMovement record
    movs = client.get(f"/api/v1/inventory/movements?product_id={p['id']}", headers=headers).json()["data"]
    sale_mov = next(m for m in movs if m["movement_type"] == "sale")
    assert Decimal(sale_mov["unit_cost"]) == Decimal("150.0000")
    assert Decimal(sale_mov["quantity_delta"]) == Decimal("-4.0000")
    assert Decimal(sale_mov["balance_after"]) == Decimal("16.0000")

