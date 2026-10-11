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


def test_category_crud_and_duplicate_rejection(client: TestClient):
    auth = register_user(client, "9876510001", "Kanakku Mart")
    headers = auth["headers"]

    # 1. Create Category
    create_res = client.post("/api/v1/categories", headers=headers, json={
        "name": "Beverages",
        "tamil_name": "பானங்கள்",
        "display_order": 1
    })
    assert create_res.status_code == 201
    cat = create_res.json()["data"]
    cat_id = cat["id"]
    assert cat["name"] == "Beverages"
    assert cat["tamil_name"] == "பானங்கள்"

    # 2. Reject Duplicate Category in same business
    dup_res = client.post("/api/v1/categories", headers=headers, json={
        "name": "beverages",  # case-insensitive check
        "display_order": 2
    })
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"

    # 3. List Categories
    list_res = client.get("/api/v1/categories", headers=headers)
    assert list_res.status_code == 200
    cats = list_res.json()["data"]
    assert len(cats) >= 1
    assert any(c["id"] == cat_id for c in cats)

    # 4. Update Category
    update_res = client.put(f"/api/v1/categories/{cat_id}", headers=headers, json={
        "name": "Cold Drinks",
        "display_order": 5
    })
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Cold Drinks"
    assert update_res.json()["data"]["display_order"] == 5

    # 5. Delete Category
    del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=headers)
    assert del_res.status_code == 200


def test_product_creation_and_sku_validation(client: TestClient):
    auth_a = register_user(client, "9876510002", "Store A")
    auth_b = register_user(client, "9876510003", "Store B")

    # 1. Create Product with SKU in Store A
    p1_res = client.post("/api/v1/products", headers=auth_a["headers"], json={
        "name": "Organic Honey 500g",
        "tamil_name": "இயற்கை தேன்",
        "sku": "HONEY-001",
        "unit": "box",
        "purchase_cost": 220.50,
        "selling_price": 310.00,
        "low_stock_threshold": 5
    })
    assert p1_res.status_code == 201
    p1 = p1_res.json()["data"]
    assert p1["name"] == "Organic Honey 500g"
    assert p1["sku"] == "HONEY-001"
    assert p1["unit"] == "box"
    assert Decimal(str(p1["current_stock"])) == Decimal("0.00")

    # 2. Duplicate SKU in Store A should be rejected with 409
    p1_dup = client.post("/api/v1/products", headers=auth_a["headers"], json={
        "name": "Different Honey",
        "sku": "honey-001",  # case-insensitive check
        "unit": "box",
        "purchase_cost": 200.00,
        "selling_price": 280.00
    })
    assert p1_dup.status_code == 409
    assert p1_dup.json()["error"]["code"] == "SKU_ALREADY_EXISTS"

    # 3. Store B can use the same SKU (tenant isolation)
    p2_store_b = client.post("/api/v1/products", headers=auth_b["headers"], json={
        "name": "Wild Honey",
        "sku": "HONEY-001",
        "unit": "box",
        "purchase_cost": 210.00,
        "selling_price": 300.00
    })
    assert p2_store_b.status_code == 201
    assert p2_store_b.json()["data"]["sku"] == "HONEY-001"


def test_decimal_precision_and_no_float_drift(client: TestClient):
    auth = register_user(client, "9876510004", "Precision Shop")
    headers = auth["headers"]

    # Exact 4-decimal place test
    prod_res = client.post("/api/v1/products", headers=headers, json={
        "name": "Precision Cable",
        "unit": "meter",
        "purchase_cost": 12.3456,
        "selling_price": 25.8750,
        "low_stock_threshold": 10.5000,
        "opening_stock": 100.2500,
        "opening_stock_cost": 12.3456
    })
    assert prod_res.status_code == 201
    prod = prod_res.json()["data"]
    assert Decimal(str(prod["purchase_cost"])) == Decimal("12.3456")
    assert Decimal(str(prod["selling_price"])) == Decimal("25.8750")
    assert Decimal(str(prod["current_stock"])) == Decimal("100.2500")


def test_opening_stock_and_movements_traceability(client: TestClient):
    auth = register_user(client, "9876510005", "Legacy Mart")
    headers = auth["headers"]

    # Create product with initial opening stock
    res = client.post("/api/v1/products", headers=headers, json={
        "name": "Basmati Rice 25kg",
        "unit": "bag",
        "purchase_cost": 1450.00,
        "selling_price": 1800.00,
        "opening_stock": 40.0,
        "opening_stock_cost": 1400.00
    })
    assert res.status_code == 201
    prod_id = res.json()["data"]["id"]
    assert Decimal(str(res.json()["data"]["current_stock"])) == Decimal("40.0")

    # Check detail endpoint returns the opening stock movement
    detail_res = client.get(f"/api/v1/products/{prod_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert len(detail["recent_movements"]) == 1
    movement = detail["recent_movements"][0]
    assert movement["movement_type"] == "opening"
    assert Decimal(str(movement["quantity_delta"])) == Decimal("40.0")
    assert Decimal(str(movement["balance_after"])) == Decimal("40.0")
    assert Decimal(str(movement["unit_cost"])) == Decimal("1400.0")
    assert "Opening stock" in movement["reason"]


def test_stock_adjustments_increase_decrease_and_reasons(client: TestClient):
    auth = register_user(client, "9876510006", "Inventory Center")
    headers = auth["headers"]

    prod_res = client.post("/api/v1/products", headers=headers, json={
        "name": "A4 Paper Bundle",
        "unit": "box",
        "purchase_cost": 250.00,
        "selling_price": 320.00,
        "opening_stock": 10.0
    })
    prod_id = prod_res.json()["data"]["id"]

    # 1. Increase stock with valid reason
    inc_res = client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": prod_id,
        "adjustment_type": "increase",
        "quantity": 15.0,
        "reason": "Found uncounted stock in backroom godown",
        "unit_cost": 240.00
    })
    assert inc_res.status_code == 201
    inc_data = inc_res.json()["data"]
    assert inc_data["movement_type"] == "adjustment_increase"
    assert Decimal(str(inc_data["quantity_delta"])) == Decimal("15.0")
    assert Decimal(str(inc_data["balance_after"])) == Decimal("25.0")

    # 2. Decrease stock with valid reason
    dec_res = client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": prod_id,
        "adjustment_type": "decrease",
        "quantity": 5.0,
        "reason": "Water damage from ceiling leak"
    })
    assert dec_res.status_code == 201
    dec_data = dec_res.json()["data"]
    assert dec_data["movement_type"] == "adjustment_decrease"
    assert Decimal(str(dec_data["quantity_delta"])) == Decimal("-5.0")
    assert Decimal(str(dec_data["balance_after"])) == Decimal("20.0")

    # 3. Check product current balance reflected accurately
    check_prod = client.get(f"/api/v1/products/{prod_id}", headers=headers)
    assert Decimal(str(check_prod.json()["data"]["current_stock"])) == Decimal("20.0")


def test_adjustment_fails_without_required_reason(client: TestClient):
    auth = register_user(client, "9876510007", "Audit Store")
    headers = auth["headers"]

    prod_res = client.post("/api/v1/products", headers=headers, json={
        "name": "Item For Audit",
        "unit": "piece",
        "selling_price": 100.00,
        "opening_stock": 5.0
    })
    prod_id = prod_res.json()["data"]["id"]

    # Reason too short / empty
    fail_res = client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": prod_id,
        "adjustment_type": "increase",
        "quantity": 2.0,
        "reason": "  "  # Blank
    })
    assert fail_res.status_code == 422


def test_strict_non_negative_stock_enforcement(client: TestClient):
    auth = register_user(client, "9876510008", "No Deficit Store")
    headers = auth["headers"]

    prod_res = client.post("/api/v1/products", headers=headers, json={
        "name": "Cereal Box",
        "unit": "box",
        "selling_price": 150.00,
        "opening_stock": 8.0
    })
    prod_id = prod_res.json()["data"]["id"]

    # Try decreasing by 10 when stock is 8 -> must reject with 400 INSUFFICIENT_STOCK
    dec_fail = client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": prod_id,
        "adjustment_type": "decrease",
        "quantity": 10.0,
        "reason": "Accidental over-reduction test"
    })
    assert dec_fail.status_code == 400
    assert dec_fail.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Confirm stock remains exactly 8.0
    check_prod = client.get(f"/api/v1/products/{prod_id}", headers=headers)
    assert Decimal(str(check_prod.json()["data"]["current_stock"])) == Decimal("8.0")


def test_low_stock_status_and_filter(client: TestClient):
    auth = register_user(client, "9876510009", "Alerts Depot")
    headers = auth["headers"]

    # Create product with threshold 10, initial stock 12
    p_res = client.post("/api/v1/products", headers=headers, json={
        "name": "Sunflower Oil 1L",
        "unit": "litre",
        "selling_price": 130.00,
        "low_stock_threshold": 10.0,
        "opening_stock": 12.0
    })
    p_id = p_res.json()["data"]["id"]
    assert p_res.json()["data"]["stock_status"] == "in_stock"

    # Decrease stock by 4 -> stock becomes 8 <= 10 (low stock!)
    client.post("/api/v1/inventory/adjustments", headers=headers, json={
        "product_id": p_id,
        "adjustment_type": "decrease",
        "quantity": 4.0,
        "reason": "Routine customer sale"
    })

    detail = client.get(f"/api/v1/products/{p_id}", headers=headers).json()["data"]
    assert detail["stock_status"] == "low_stock"
    assert Decimal(str(detail["current_stock"])) == Decimal("8.0")

    # Filter by low_stock=true
    filter_res = client.get("/api/v1/products?low_stock=true", headers=headers)
    assert filter_res.status_code == 200
    low_items = filter_res.json()["data"]
    assert any(x["id"] == p_id for x in low_items)


def test_product_search_and_deactivation(client: TestClient):
    auth = register_user(client, "9876510010", "Search Hub")
    headers = auth["headers"]

    client.post("/api/v1/products", headers=headers, json={
        "name": "Apple Royal Gala",
        "sku": "APP-GALA-01",
        "unit": "kg",
        "selling_price": 180.00
    })
    client.post("/api/v1/products", headers=headers, json={
        "name": "Banana Cavendish",
        "sku": "BAN-CAV-02",
        "unit": "dozen",
        "selling_price": 60.00
    })

    # Search by SKU
    search_res = client.get("/api/v1/products?search=GALA", headers=headers)
    assert search_res.status_code == 200
    items = search_res.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Apple Royal Gala"

    # Deactivate product
    apple_id = items[0]["id"]
    deact_res = client.patch(f"/api/v1/products/{apple_id}/status", headers=headers, json={"is_active": False})
    assert deact_res.status_code == 200
    assert deact_res.json()["data"]["is_active"] is False

    # Active filter check
    active_res = client.get("/api/v1/products?is_active=true", headers=headers)
    active_ids = [x["id"] for x in active_res.json()["data"]]
    assert apple_id not in active_ids


def test_cross_tenant_isolation_rejection(client: TestClient):
    tenant_a = register_user(client, "9876510011", "Tenant Alpha")
    tenant_b = register_user(client, "9876510012", "Tenant Beta")

    # Tenant Alpha creates a product
    p_a = client.post("/api/v1/products", headers=tenant_a["headers"], json={
        "name": "Alpha Secret Formula",
        "unit": "litre",
        "selling_price": 999.00,
        "opening_stock": 5.0
    }).json()["data"]

    alpha_prod_id = p_a["id"]

    # Tenant Beta attempts to access Tenant Alpha's product -> 404
    get_fail = client.get(f"/api/v1/products/{alpha_prod_id}", headers=tenant_b["headers"])
    assert get_fail.status_code == 404

    # Tenant Beta attempts to adjust stock of Tenant Alpha's product -> 404
    adjust_fail = client.post("/api/v1/inventory/adjustments", headers=tenant_b["headers"], json={
        "product_id": alpha_prod_id,
        "adjustment_type": "increase",
        "quantity": 10.0,
        "reason": "Hacking stock attempt"
    })
    assert adjust_fail.status_code == 404

    # Tenant Beta attempts to edit Tenant Alpha's product -> 404
    edit_fail = client.put(f"/api/v1/products/{alpha_prod_id}", headers=tenant_b["headers"], json={
        "name": "Stolen Formula"
    })
    assert edit_fail.status_code == 404


def test_inventory_overview_dashboard_metrics(client: TestClient):
    auth = register_user(client, "9876510013", "Metrics Emporium")
    headers = auth["headers"]

    # 1. Product with good stock (5 * ₹100 = ₹500)
    client.post("/api/v1/products", headers=headers, json={
        "name": "Good Stock Item",
        "purchase_cost": 100.00,
        "selling_price": 150.00,
        "low_stock_threshold": 2.0,
        "opening_stock": 5.0
    })

    # 2. Product with low stock (1 <= 3) (1 * ₹200 = ₹200)
    client.post("/api/v1/products", headers=headers, json={
        "name": "Low Stock Item",
        "purchase_cost": 200.00,
        "selling_price": 280.00,
        "low_stock_threshold": 3.0,
        "opening_stock": 1.0
    })

    # 3. Product with 0 stock (out of stock)
    client.post("/api/v1/products", headers=headers, json={
        "name": "Out of Stock Item",
        "purchase_cost": 50.00,
        "selling_price": 80.00,
        "low_stock_threshold": 5.0,
        "opening_stock": 0.0
    })

    ov_res = client.get("/api/v1/inventory/overview", headers=headers)
    assert ov_res.status_code == 200
    ov = ov_res.json()["data"]
    assert ov["total_products"] == 3
    assert ov["active_products"] == 3
    assert ov["low_stock_products"] == 1
    assert ov["out_of_stock_products"] == 1
    # ₹500 + ₹200 = ₹700
    assert Decimal(str(ov["total_stock_value"])) == Decimal("700.0000")
