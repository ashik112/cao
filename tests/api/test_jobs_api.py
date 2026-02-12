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


def test_resume_job_not_found(client: TestClient):
    response = client.post("/api/v1/jobs/missing-job/resume")
    assert response.status_code == 404


def test_resume_job_success(client: TestClient):
    create_resp = client.post(
        "/api/v1/jobs",
        json={"feature_name": "business_plan", "input_data": {"business_name": "resume-test"}},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["job_id"]

    resume_resp = client.post(f"/api/v1/jobs/{job_id}/resume")
    assert resume_resp.status_code == 200
    payload = resume_resp.json()
    assert payload["success"] is True
    assert payload["job_id"] == job_id
    assert payload["new_status"] == "RUNNING"
    assert payload["resuming_from_step"] == "prompt_enhancer"
