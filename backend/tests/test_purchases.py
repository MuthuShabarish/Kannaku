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
# SUPPLIER MANAGEMENT & AP LEDGER TESTS
# ============================================================================

def test_supplier_crud_and_duplicate_name_rejection(client: TestClient):
    auth = register_user(client, "9876540001", "Murugan Hardware")
    headers = auth["headers"]

    # 1. Create supplier
    res = client.post(
        "/api/v1/suppliers",
        headers=headers,
        json={
            "name": "Tata Steel Traders",
            "phone": "9876543210",
            "email": "tata@traders.com",
            "address": "123 Industrial Area, Chennai",
            "notes": "Net 30 payment terms"
        }
    )
    assert res.status_code == 201
    sup_data = res.json()["data"]
    supplier_id = sup_data["id"]
    assert sup_data["name"] == "Tata Steel Traders"
    assert Decimal(sup_data["current_balance"]) == Decimal("0.0000")
    assert sup_data["is_active"] is True

    # 2. Reject duplicate supplier name within same business (case-insensitive)
    dup_res = client.post(
        "/api/v1/suppliers",
        headers=headers,
        json={"name": "  tata steel traders  ", "phone": "9876543299"}
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "SUPPLIER_NAME_EXISTS"

    # 3. Update supplier
    upd_res = client.put(
        f"/api/v1/suppliers/{supplier_id}",
        headers=headers,
        json={"notes": "Updated terms: 2% cash discount within 10 days"}
    )
    assert upd_res.status_code == 200
    assert "2% cash discount" in upd_res.json()["data"]["notes"]

    # 4. List suppliers
    list_res = client.get("/api/v1/suppliers?search=tata", headers=headers)
    assert list_res.status_code == 200
    assert any(s["id"] == supplier_id for s in list_res.json()["data"])


def test_supplier_ledger_and_payment_settlement(client: TestClient):
    auth = register_user(client, "9876540002", "Krishna Agro Stores")
    headers = auth["headers"]

    # Create supplier
    res = client.post("/api/v1/suppliers", headers=headers, json={"name": "Godrej Agrovet"})
    supplier_id = res.json()["data"]["id"]

    # Create product
    prod = create_sample_product(client, headers, "Cattle Feed 50kg", "800.0000", "950.0000", "0.0000")

    # Purchase on credit: 2 bags @ ₹800 = ₹1,600 (Pay ₹600 now, ₹1,000 credit)
    pur_res = client.post("/api/v1/purchases", headers=headers, json={
        "supplier_id": supplier_id,
        "payment_method": "credit",
        "paid_amount": "600.0000",
        "items": [{"product_id": prod["id"], "quantity": "2.0000", "unit_cost": "800.0000"}]
    })
    assert pur_res.status_code == 201
    assert pur_res.json()["data"]["credit_amount"] == "1000.0000"

    # Reject payment amount <= 0
    neg_res = client.post(f"/api/v1/suppliers/{supplier_id}/payments", headers=headers, json={"amount": -50.0, "payment_mode": "cash"})
    assert neg_res.status_code == 422

    # Reject oversettlement (paying 1200 when balance is 1000)
    over_res = client.post(f"/api/v1/suppliers/{supplier_id}/payments", headers=headers, json={"amount": "1200.0000", "payment_mode": "cash"})
    assert over_res.status_code == 400
    assert over_res.json()["error"]["code"] == "SETTLEMENT_EXCEEDS_BALANCE"

    # Valid partial settlement: pay ₹400 via UPI
    pay1_res = client.post(f"/api/v1/suppliers/{supplier_id}/payments", headers=headers, json={"amount": "400.0000", "payment_mode": "upi", "notes": "Part payment via GPay"})
    assert pay1_res.status_code == 201
    entry1 = pay1_res.json()["data"]
    assert Decimal(entry1["amount"]) == Decimal("400.0000")
    assert Decimal(entry1["balance_after"]) == Decimal("600.0000")
    assert entry1["entry_type"] == "payment_made"

    # Valid full remaining settlement: pay ₹600 via Bank Transfer
    pay2_res = client.post(f"/api/v1/suppliers/{supplier_id}/payments", headers=headers, json={"amount": "600.0000", "payment_mode": "bank_transfer"})
    assert pay2_res.status_code == 201
    assert Decimal(pay2_res.json()["data"]["balance_after"]) == Decimal("0.0000")

    # Reject payment when balance is 0
    zero_res = client.post(f"/api/v1/suppliers/{supplier_id}/payments", headers=headers, json={"amount": "100.0000", "payment_mode": "cash"})
    assert zero_res.status_code == 400
    assert zero_res.json()["error"]["code"] == "NO_OUTSTANDING_BALANCE"

    # Fetch supplier detail with ledger history
    detail_res = client.get(f"/api/v1/suppliers/{supplier_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert Decimal(detail["current_balance"]) == Decimal("0.0000")
    assert len(detail["recent_entries"]) == 3  # 1 credit purchase + 2 payments

    # Verify ledger endpoint
    ledger_res = client.get(f"/api/v1/suppliers/{supplier_id}/ledger", headers=headers)
    assert ledger_res.status_code == 200
    assert len(ledger_res.json()["data"]) == 3


# ============================================================================
# PURCHASE RECEIVING & MOVING AVERAGE COSTING TESTS
# ============================================================================

def test_successful_cash_purchase_with_stock_receipt_and_mac(client: TestClient):
    auth = register_user(client, "9876540003", "Kovai Cement Depot")
    headers = auth["headers"]

    # Initial product: 10 units @ ₹100 opening cost
    prod = create_sample_product(client, headers, "Ultrasharp Nails", "100.0000", "150.0000", "10.0000")

    # Purchase 10 units @ ₹200 cash
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "payment_method": "cash",
            "items": [
                {"product_id": prod["id"], "quantity": "10.0000", "unit_cost": "200.0000", "discount_amount": "0.0000"}
            ],
            "discount_amount": "0.0000",
            "notes": "Direct shop restock"
        }
    )
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert Decimal(data["total_amount"]) == Decimal("2000.0000")
    assert Decimal(data["paid_amount"]) == Decimal("2000.0000")
    assert Decimal(data["credit_amount"]) == Decimal("0.0000")
    assert data["payment_status"] == "paid"
    assert len(data["items"]) == 1
    assert Decimal(data["items"][0]["effective_unit_cost"]) == Decimal("200.0000")

    # Verify inventory balance updated to 20 units
    prod_check = client.get(f"/api/v1/products/{prod['id']}", headers=headers).json()["data"]
    assert Decimal(prod_check["current_stock"]) == Decimal("20.0000")

    # Verify product purchase_cost updated to latest landed cost ₹200.0000
    assert Decimal(prod_check["purchase_cost"]) == Decimal("200.0000")

    # Verify StockMovement entry
    mov_res = client.get(f"/api/v1/inventory/movements?product_id={prod['id']}", headers=headers)
    assert mov_res.status_code == 200
    movements = mov_res.json()["data"]
    pur_mov = next(m for m in movements if m["movement_type"] == "purchase")
    assert Decimal(pur_mov["quantity_delta"]) == Decimal("10.0000")
    assert Decimal(pur_mov["balance_after"]) == Decimal("20.0000")
    assert Decimal(pur_mov["unit_cost"]) == Decimal("200.0000")


def test_zero_opening_stock_purchase_mac(client: TestClient):
    auth = register_user(client, "9876540004", "Pipe House")
    headers = auth["headers"]

    # Product with 0 opening stock
    prod = create_sample_product(client, headers, "Zero Stock Pipe", "0.0000", "150.0000", "0.0000")

    # Purchase 5 units @ ₹125.50
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "payment_method": "cash",
            "items": [
                {"product_id": prod["id"], "quantity": "5.0000", "unit_cost": "125.5000"}
            ]
        }
    )
    assert res.status_code == 201

    # Verify inventory balance is 5 units
    prod_check = client.get(f"/api/v1/products/{prod['id']}", headers=headers).json()["data"]
    assert Decimal(prod_check["current_stock"]) == Decimal("5.0000")
    assert Decimal(prod_check["purchase_cost"]) == Decimal("125.5000")


def test_purchase_discount_allocation_and_landed_cost(client: TestClient):
    auth = register_user(client, "9876540005", "Discount Mart")
    headers = auth["headers"]

    prod_a = create_sample_product(client, headers, "Item Alpha", "0.0000", "150.0000", "0.0000")
    prod_b = create_sample_product(client, headers, "Item Beta", "0.0000", "50.0000", "0.0000")

    # Purchase:
    # Item A: 10 units @ ₹100, line discount ₹100 -> line net = ₹900
    # Item B: 10 units @ ₹30.00, line discount ₹0 -> line net = ₹300
    # Subtotal = ₹1,200
    # Overall invoice discount = ₹120 (10% of subtotal)
    # Total invoice amount = ₹1,080
    # Item A allocated overall discount: (900 / 1200) * 120 = ₹90 -> landed net = ₹810 -> effective unit cost = ₹81.0000
    # Item B allocated overall discount: (300 / 1200) * 120 = ₹30 -> landed net = ₹270 -> effective unit cost = ₹27.0000
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "payment_method": "cash",
            "discount_amount": "120.0000",
            "items": [
                {"product_id": prod_a["id"], "quantity": "10.0000", "unit_cost": "100.0000", "discount_amount": "100.0000"},
                {"product_id": prod_b["id"], "quantity": "10.0000", "unit_cost": "30.0000", "discount_amount": "0.0000"}
            ]
        }
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert Decimal(data["subtotal_amount"]) == Decimal("1200.0000")
    assert Decimal(data["discount_amount"]) == Decimal("120.0000")
    assert Decimal(data["total_amount"]) == Decimal("1080.0000")
    assert Decimal(data["paid_amount"]) == Decimal("1080.0000")

    items_map = {item["product_id"]: item for item in data["items"]}
    assert Decimal(items_map[prod_a["id"]]["effective_unit_cost"]) == Decimal("81.0000")
    assert Decimal(items_map[prod_b["id"]]["effective_unit_cost"]) == Decimal("27.0000")


def test_credit_purchase_and_supplier_ap_ledger(client: TestClient):
    auth = register_user(client, "9876540006", "Steel City")
    headers = auth["headers"]

    sup_res = client.post("/api/v1/suppliers", headers=headers, json={"name": "Steel Authority"})
    supplier_id = sup_res.json()["data"]["id"]

    prod = create_sample_product(client, headers, "Rebar Rods", "500.0000", "650.0000", "0.0000")

    # Partial credit purchase: Total ₹5,000, Pay ₹2,000 now, ₹3,000 credit
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_ref": "SUP-BILL-9901",
            "payment_method": "credit",
            "paid_amount": "2000.0000",
            "items": [
                {"product_id": prod["id"], "quantity": "10.0000", "unit_cost": "500.0000"}
            ]
        }
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert Decimal(data["total_amount"]) == Decimal("5000.0000")
    assert Decimal(data["paid_amount"]) == Decimal("2000.0000")
    assert Decimal(data["credit_amount"]) == Decimal("3000.0000")
    assert data["payment_status"] == "partial"

    # Verify supplier balance increased by credit_amount ₹3,000
    sup_check = client.get(f"/api/v1/suppliers/{supplier_id}", headers=headers).json()["data"]
    assert Decimal(sup_check["current_balance"]) == Decimal("3000.0000")
    assert len(sup_check["recent_entries"]) == 1
    assert sup_check["recent_entries"][0]["entry_type"] == "credit_purchase"
    assert Decimal(sup_check["recent_entries"][0]["amount"]) == Decimal("3000.0000")


def test_split_payment_purchase(client: TestClient):
    auth = register_user(client, "9876540007", "Timber Depot")
    headers = auth["headers"]

    sup_res = client.post("/api/v1/suppliers", headers=headers, json={"name": "Timber Depot Supplier"})
    supplier_id = sup_res.json()["data"]["id"]

    prod = create_sample_product(client, headers, "Teak Planks", "500.0000", "700.0000", "0.0000")

    # Total bill = ₹1,000. Split: Cash ₹300, UPI ₹500, Remaining ₹200 on Credit
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "payment_method": "split",
            "split_payments": [
                {"mode": "cash", "amount": "300.0000"},
                {"mode": "upi", "amount": "500.0000"}
            ],
            "items": [
                {"product_id": prod["id"], "quantity": "2.0000", "unit_cost": "500.0000"}
            ]
        }
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert Decimal(data["total_amount"]) == Decimal("1000.0000")
    assert Decimal(data["paid_amount"]) == Decimal("800.0000")
    assert Decimal(data["credit_amount"]) == Decimal("200.0000")
    assert data["payment_status"] == "partial"
    assert len(data["payments"]) == 2

    # Verify supplier balance is ₹200
    sup_check = client.get(f"/api/v1/suppliers/{supplier_id}", headers=headers).json()["data"]
    assert Decimal(sup_check["current_balance"]) == Decimal("200.0000")


def test_purchase_idempotency_key_duplicate_prevention(client: TestClient):
    auth = register_user(client, "9876540008", "Idempotent Depot")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Paint Bucket", "400.0000", "550.0000", "5.0000")
    idem_key = f"purchase-idem-{uuid.uuid4()}"

    payload = {
        "idempotency_key": idem_key,
        "payment_method": "cash",
        "items": [
            {"product_id": prod["id"], "quantity": "5.0000", "unit_cost": "400.0000"}
        ]
    }

    # First request
    res1 = client.post("/api/v1/purchases", headers=headers, json=payload)
    assert res1.status_code == 201
    inv_num_1 = res1.json()["data"]["invoice_number"]

    # Second request with same idempotency key
    res2 = client.post("/api/v1/purchases", headers=headers, json=payload)
    assert res2.status_code == 201
    assert res2.json()["data"]["invoice_number"] == inv_num_1

    # Verify inventory received ONLY ONCE (5 initial + 5 received = 10, NOT 15)
    prod_check = client.get(f"/api/v1/products/{prod['id']}", headers=headers).json()["data"]
    assert Decimal(prod_check["current_stock"]) == Decimal("10.0000")


def test_historical_purchase_invoice_integrity(client: TestClient):
    auth = register_user(client, "9876540009", "Brick Kiln")
    headers = auth["headers"]

    prod = create_sample_product(client, headers, "Standard Brick", "12.0000", "18.0000", "0.0000")

    # Purchase 100 bricks @ ₹12.00
    res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "payment_method": "cash",
            "items": [{"product_id": prod["id"], "quantity": "100.0000", "unit_cost": "12.0000"}]
        }
    )
    assert res.status_code == 201
    purchase_id = res.json()["data"]["id"]

    # Now edit product in catalog: name and price
    up_res = client.put(f"/api/v1/products/{prod['id']}", headers=headers, json={
        "name": "Altered Brick Premium",
        "purchase_cost": "25.0000"
    })
    assert up_res.status_code == 200

    # Query purchase details: snapshot of product_name and unit_cost must remain unchanged!
    detail_res = client.get(f"/api/v1/purchases/{purchase_id}", headers=headers)
    assert detail_res.status_code == 200
    item = detail_res.json()["data"]["items"][0]
    assert item["product_name"] == "Standard Brick"
    assert Decimal(item["unit_cost"]) == Decimal("12.0000")


def test_cross_tenant_purchase_and_supplier_isolation(client: TestClient):
    auth_a = register_user(client, "9876540010", "Tenant A Depot")
    auth_b = register_user(client, "9876540011", "Tenant B Depot")

    # Create supplier in Tenant A
    sup_res = client.post("/api/v1/suppliers", headers=auth_a["headers"], json={"name": "Tenant A Exclusive Supplier"})
    supplier_a_id = sup_res.json()["data"]["id"]

    # Tenant B tries to fetch Tenant A supplier -> 404
    get_res = client.get(f"/api/v1/suppliers/{supplier_a_id}", headers=auth_b["headers"])
    assert get_res.status_code == 404

    # Tenant B tries to record payment to Tenant A supplier -> 404
    pay_res = client.post(f"/api/v1/suppliers/{supplier_a_id}/payments", headers=auth_b["headers"], json={"amount": "100.0000", "payment_mode": "cash"})
    assert pay_res.status_code == 404


def test_failed_purchase_leaves_zero_partial_records(client: TestClient):
    auth = register_user(client, "9876540012", "Glass Mart")
    headers = auth["headers"]

    sup_res = client.post("/api/v1/suppliers", headers=headers, json={"name": "Glass Suppliers"})
    supplier_id = sup_res.json()["data"]["id"]

    prod = create_sample_product(client, headers, "Window Glass", "200.0000", "300.0000", "5.0000")

    # Attempt purchase with negative unit cost (-100) -> validation rejection
    fail_res = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "payment_method": "credit",
            "items": [{"product_id": prod["id"], "quantity": "10.0000", "unit_cost": "-100.0000"}]
        }
    )
    assert fail_res.status_code in (400, 422)

    # Verify no purchases exist
    purchases = client.get("/api/v1/purchases", headers=headers).json()["data"]
    assert len(purchases) == 0

    # Verify stock is unchanged
    prod_check = client.get(f"/api/v1/products/{prod['id']}", headers=headers).json()["data"]
    assert Decimal(prod_check["current_stock"]) == Decimal("5.0000")


def test_purchases_overview_metrics(client: TestClient):
    auth = register_user(client, "9876540013", "Overview Enterprise")
    headers = auth["headers"]

    sup = client.post("/api/v1/suppliers", headers=headers, json={"name": "Wholesale Distributor"}).json()["data"]
    prod = create_sample_product(client, headers, "Stock Gadget", "50.0000", "80.0000", "10.0000")

    # Purchase 1: Cash 100
    client.post("/api/v1/purchases", headers=headers, json={
        "items": [{"product_id": prod["id"], "quantity": "2.0000", "unit_cost": "50.0000"}],
        "payment_method": "cash"
    })

    # Purchase 2: Credit 300
    client.post("/api/v1/purchases", headers=headers, json={
        "supplier_id": sup["id"],
        "items": [{"product_id": prod["id"], "quantity": "3.0000", "unit_cost": "100.0000"}],
        "payment_method": "credit",
        "paid_amount": "0.0000"
    })

    # Fetch overview
    res = client.get("/api/v1/purchases/overview", headers=headers)
    assert res.status_code == 200
    metrics = res.json()["data"]
    assert metrics["total_purchases_count"] == 2
    assert Decimal(metrics["total_purchases_amount"]) == Decimal("400.0000")
    assert Decimal(metrics["total_paid_amount"]) == Decimal("100.0000")
    assert Decimal(metrics["total_credit_amount"]) == Decimal("300.0000")
    assert metrics["total_suppliers"] == 1
    assert Decimal(metrics["total_payable"]) == Decimal("300.0000")
