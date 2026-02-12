from fastapi.testclient import TestClient

def test_start_job_success(client: TestClient):
    response = client.post(
        "/api/v1/jobs",
        json={"feature_name": "business_plan", "input_data": {"business_name": "test"}}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "job_id" in data
    assert data["status"] == "PENDING"

def test_start_job_invalid_feature(client: TestClient):
    response = client.post(
        "/api/v1/jobs",
        json={"feature_name": "unknown_feature", "input_data": {}}
    )
    assert response.status_code == 400

def test_get_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
