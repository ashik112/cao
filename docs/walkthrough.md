# CAO v1.3 Walkthrough

## Overview
This walkthrough demonstrates the implemented Centralized API Orchestrator (CAO) v1.3 system. The system uses a modular architecture with FastAPI for the API layer and Celery for background task processing, backed by Redis and PostgreSQL.

## Features Implemented
- **Repository Structure**: Modular layout separating specific concerns (`app/`, `worker/`, `alembic/`).
- **Configuration**: Unified registry for services and features in [app/config.py](../backend/app/config.py).
- **Core Logic**:
    - **Orchestration**: [OrchestratorService](../backend/app/services/orchestrator_service.py) handles step execution, state management, and error handling.
    - **Concurrency**: Lease-based distributed semaphore using Redis Lua scripts ([LimiterService](../backend/app/services/limiter_service.py)).
    - **Idempotency**: Step-level idempotency to prevent duplicate executions.
    - **Resiliency**: Retry logic, stuck job detection, and exponential backoff.
- **API**:
    - `POST /api/v1/jobs`: Start a new job.
    - `POST /api/v1/jobs/{job_id}/resume`: Resume a failed or stuck job.
    - `WS /ws/{job_id}`: Real-time status updates via WebSocket.
    - `GET /health` & `GET /health/services`: Health checks.
- **Workers**: Scalable Celery workers with different queues (`heavy`, `medium`, `default`).

## How to Run

1.  **Start Infrastructure**:
    ```bash
    cd backend
    docker-compose up --build
    ```

2.  **Apply Migrations**:
    The system is configured to use Alembic. You may need to run migrations externally or add a migration step to the startup command if they are not applied automatically.
    ```bash
    # Inside the api container or locally
    alembic upgrade head
    ```

## Verification

### 1. Start a Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"feature_name":"business_plan","input_data":{"business_name":"AI Toys"}}'
```
Expected Response:
```json
{
    "success": true,
    "job_id": "<uuid>",
    "monitor_url": "ws://localhost:8000/ws/<uuid>",
    "status": "PENDING"
}
```

### 2. Monitor via WebSocket
Connect to `ws://localhost:8000/ws/<job_id>` to receive real-time updates.

### 3. Check Health
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/services
```
