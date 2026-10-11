import uuid


def test_register_owner_success(client):
    payload = {
        "phone": "9876543210",
        "pin_or_password": "8421",
        "full_name": "Karthik Vel",
        "business_name": "Karthik Veggies",
        "category": "Produce",
        "currency_code": "INR",
        "currency_symbol": "₹",
        "default_language": "ta"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["user"]["phone"] == "+919876543210"
    assert data["user"]["role"] == "owner"
    assert data["business"]["name"] == "Karthik Veggies"
    assert data["business"]["currency_code"] == "INR"
    assert "access_token" in data["tokens"]
    assert "emergency_recovery_key" in data
    assert len(data["emergency_recovery_key"]) >= 16


def test_register_duplicate_phone_rejected(client):
    payload = {
        "phone": "9876543211",
        "pin_or_password": "8421",
        "full_name": "Ravi",
        "business_name": "Ravi Tea",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt to register identical phone
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    err = res2.json()
    assert err["success"] is False
    assert err["error"]["code"] == "PHONE_ALREADY_REGISTERED"


def test_register_weak_pin_rejected(client):
    payload = {
        "phone": "9876543212",
        "pin_or_password": "1234",  # sequential
        "full_name": "Ravi",
        "business_name": "Ravi Tea",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422
    err = res.json()
    assert err["success"] is False
    assert "pin_or_password" in err["error"]["field"]


def test_login_success_and_me_endpoint(client):
    # 1. Register user
    reg_payload = {
        "phone": "9876543220",
        "pin_or_password": "7890",
        "full_name": "Sundar",
        "business_name": "Sundar Footwear"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "phone": "9876543220",
        "pin_or_password": "7890"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    token = res.json()["data"]["tokens"]["access_token"]
    assert token is not None

    # 3. Access /me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["user"]["phone"] == "+919876543220"
    assert me_data["business"]["name"] == "Sundar Footwear"


def test_login_invalid_pin_failure(client):
    reg_payload = {
        "phone": "9876543230",
        "pin_or_password": "7890",
        "full_name": "Muthu",
        "business_name": "Muthu Sweets"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Wrong PIN
    res = client.post("/api/v1/auth/login", json={"phone": "9876543230", "pin_or_password": "9999"})
    assert res.status_code == 401
    err = res.json()
    assert err["success"] is False
    assert err["error"]["code"] == "INVALID_CREDENTIALS"


def test_unauthorized_access_rejected(client):
    # Access /me with no token
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["success"] is False

    # Access /me with invalid token
    res_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert res_bad.status_code == 401
    assert res_bad.json()["success"] is False


def test_tenant_isolation_enforcement(client):
    # Register Business A
    client.post("/api/v1/auth/register", json={
        "phone": "9876543241",
        "pin_or_password": "8852",
        "full_name": "Owner A",
        "business_name": "Business A"
    })
    login_a = client.post("/api/v1/auth/login", json={"phone": "9876543241", "pin_or_password": "8852"})
    token_a = login_a.json()["data"]["tokens"]["access_token"]

    # Register Business B
    client.post("/api/v1/auth/register", json={
        "phone": "9876543242",
        "pin_or_password": "8852",
        "full_name": "Owner B",
        "business_name": "Business B"
    })

    # User A tries to spoof X-Business-ID with a random or Business B UUID
    spoofed_uuid = str(uuid.uuid4())
    headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Business-ID": spoofed_uuid
    }
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CROSS_TENANT_ACCESS_DENIED"
