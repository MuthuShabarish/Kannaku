def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["app_name"] == "Kanakku (கணக்கு)"
    assert data["data"]["default_currency"] == "INR"
    assert data["data"]["default_currency_symbol"] == "₹"


def test_api_v1_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "database" in data["data"]
