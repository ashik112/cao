from fastapi.testclient import TestClient

from app.config import SERVICES


def test_health_services_endpoint(client: TestClient, requests_mock):
    for service_name, conf in SERVICES.items():
        url = conf["base_url"].rstrip("/") + conf.get("health_path", "/health")
        requests_mock.get(url, status_code=200)

    response = client.get("/api/v1/health/services")
    assert response.status_code == 200
    payload = response.json()

    assert set(payload.keys()) == set(SERVICES.keys())
    for service_name in SERVICES.keys():
        assert payload[service_name]["ok"] is True
        assert payload[service_name]["status_code"] == 200
