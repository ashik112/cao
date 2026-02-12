# CAO Gateway

CAO Gateway is an orchestration API for multi-step AI workflows.  
It accepts job requests, schedules step execution through Celery queues, tracks state in Postgres, coordinates concurrency with Redis leases, and streams progress events over WebSocket.

## What This Project Is For

Use this project when you need to:
- Accept a single user request and run multiple backend services in sequence.
- Enforce queue-based execution per service type (`heavy`, `medium`, `default`).
- Retry and recover from transient failures (timeouts, service unavailable, DB/Redis outages).
- Monitor job progress in real time over WebSocket.
- Pause/resume failed jobs from the current step.

## High-Level Architecture

- **FastAPI (`api`)**: HTTP + WebSocket endpoints.
- **Celery Workers (`worker_heavy`, `worker_medium`, `worker_default`)**: execute job steps by queue.
- **Celery Beat (`beat`)**: periodic maintenance tasks.
- **PostgreSQL (`db`)**: persistent job state.
- **Redis (`redis`)**: Celery broker/backend, lease counters, WebSocket pub/sub.
- **External AI services**: called through HTTP according to configured feature recipes.

Flow:
1. Client creates a job via `POST /api/v1/jobs`.
2. First step is queued to the queue configured for that service.
3. Worker executes step via `OrchestratorService`.
4. Progress/error events are published to Redis and consumed via WebSocket.
5. If steps remain, next step is queued automatically; else job is marked completed.

## Feature Recipes and Queues

Defined in `app/config.py`:

- `business_plan`: `prompt_enhancer -> fast_chat_llm -> summarizer_pro -> email_notifier`
- `viral_video`: `prompt_enhancer -> video_gen_v2 -> email_notifier`

Each service has:
- queue mapping
- concurrency limit
- timeout
- lease TTL
- max step attempts
- base URL + paths

## Repository Structure

- `app/`: API, schemas, service clients, orchestration logic, repositories.
- `worker/`: Celery tasks.
- `alembic/`: migration environment and versions.
- `tests/`: API + unit tests.
- `docker-compose.yml`: local stack orchestration.
- `docker-entrypoint.sh`: startup script (user mapping + migrations for API startup).

## Prerequisites

- Docker + Docker Compose plugin (`docker compose`)
- (Optional) Python 3.9+ for local non-Docker execution

## Quick Start (Docker Recommended)

### 1) Start the stack

```bash
docker compose up --build -d
```

This brings up:
- `redis`
- `db`
- `api`
- `worker_heavy`
- `worker_medium`
- `worker_default`
- `beat`

### 2) Verify API health

```bash
curl http://localhost:8000/api/v1/health
```

Expected:

```json
{"ok": true}
```

### 3) Verify downstream service reachability

```bash
curl http://localhost:8000/api/v1/health/services
```

This reports status per configured external service.

## Configuration

Environment variables are read in `app/config.py`.

Core:
- `DATABASE_URL` (default: `postgresql://user:pass@db:5432/orchestrator`)
- `REDIS_URL` (default: `redis://redis:6379/0`)
- `INTERNAL_API_KEY` (optional, forwarded to downstream services)

Timeouts and periodic checks:
- `HTTP_CONNECT_TIMEOUT_S` (default `3.0`)
- `HTTP_READ_TIMEOUT_S` (default `30.0`)
- `JOB_STUCK_SECONDS` (default `7200`)
- `SANITY_CHECK_INTERVAL_SECONDS` (default `60`)

Service URLs:
- `VIDEO_GEN_V2_URL`
- `FAST_CHAT_LLM_URL`
- `SUMMARIZER_PRO_URL`
- `PROMPT_ENHANCER_URL`
- `EMAIL_NOTIFIER_URL`

API startup migration flags:
- `RUN_MIGRATIONS_ON_STARTUP` (default `true` in compose for `api`)
- `MIGRATION_MAX_ATTEMPTS` (default `20`)
- `MIGRATION_RETRY_SLEEP_SECONDS` (default `2`)

## Database and Migrations

### Automatic migrations on API startup

`docker-entrypoint.sh` runs `alembic upgrade head` before starting `uvicorn` (for API command only).

### Create a new migration

Run inside API container:

```bash
docker compose exec api alembic revision --autogenerate -m "describe_change"
```

Generated migration files are created under `alembic/versions/` and should be committed.

### Apply migrations manually

```bash
docker compose exec api alembic upgrade head
```

## Running Tests

### Preferred (existing script)

```bash
bash run_tests.sh
```

What it does:
1. Builds test image (`cao-tests`)
2. Runs `pytest -v` in container with project mounted

### Alternative

```bash
docker compose run --rm api pytest -q
```

## API Usage

Base URL (local): `http://localhost:8000`

### Create Job

`POST /api/v1/jobs`

Request:

```json
{
  "feature_name": "business_plan",
  "input_data": {
    "business_name": "Acme Labs"
  }
}
```

Response (example):

```json
{
  "success": true,
  "job_id": "uuid",
  "monitor_url": "ws://localhost:8000/ws/uuid",
  "status": "PENDING"
}
```

### Resume Job

`POST /api/v1/jobs/{job_id}/resume`

Used when a failed job is retryable and should continue from current step index.

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/services`

## WebSocket Monitoring

Connect to:

```text
ws://localhost:8000/ws/{job_id}
```

Server sends:
- `WS_CONNECTED`
- `WAITING_FOR_SLOT`
- `STEP_STARTED`
- `STEP_COMPLETED`
- `JOB_COMPLETED`
- `JOB_ERROR`

## Celery Queues and Workers

Workers are pinned to queues in `docker-compose.yml`:
- `worker_heavy` -> queue `heavy`
- `worker_medium` -> queue `medium`
- `worker_default` -> queue `default`

Beat schedules periodic tasks:
- `sanity_check_stuck_jobs`
- `reap_expired_leases`

## Local Development (Without Docker)

1. Create venv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Provide Postgres + Redis locally and set env vars.
3. Run migrations:

```bash
alembic upgrade head
```

4. Run API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. Run workers (separate terminals):

```bash
celery -A app.celery_app.celery_app worker -Q heavy --concurrency=2 --loglevel=info
celery -A app.celery_app.celery_app worker -Q medium --concurrency=10 --loglevel=info
celery -A app.celery_app.celery_app worker -Q default --concurrency=50 --loglevel=info
celery -A app.celery_app.celery_app beat --loglevel=info
```

## Operational Notes

- `celerybeat-schedule` is a runtime artifact and should be gitignored.
- Use `docker compose logs -f api` (or workers) for troubleshooting.
- If external services are down, jobs may fail with retryable errors depending on status code and exception type.
- Job records store context and step outputs in JSON (`job.context`).

## Common Commands

```bash
# Start everything
docker compose up --build -d

# Stop everything
docker compose down

# Restart API only
docker compose up -d --build api

# View API logs
docker compose logs -f api

# Create migration
docker compose exec api alembic revision --autogenerate -m "message"

# Apply migrations
docker compose exec api alembic upgrade head

# Run tests
bash run_tests.sh
```

## Troubleshooting

- **Migration not generated on host**  
  Ensure command is run in container with project bind mount (`.:/app`).  
  Current setup supports this; generated files should appear in `alembic/versions/`.

- **`ModuleNotFoundError: app` in tests**  
  Ensure tests run with repository root on `PYTHONPATH` (handled by `pytest.ini` and `run_tests.sh`).

- **API starts before DB is ready**  
  Entrypoint retries migrations (`MIGRATION_MAX_ATTEMPTS`, `MIGRATION_RETRY_SLEEP_SECONDS`).

- **Service health check failures**  
  Verify configured service URLs and network routing from containers.

## License

Add your project license details here.
