# fal-prep

Small FastAPI exercises for fal.ai interview prep.

This repo currently implements a minimal in-memory job queue API. Clients submit prompt jobs, a background worker simulates model inference, and the API exposes endpoints for checking job status, listing jobs, cancelling queued/running jobs, and manually processing a queued job.

## Requirements

- Python 3.12
- `uv`
- Optional: `mise` for tool and task management

The project includes a devcontainer that installs Python 3.12, `mise`, and the Python dependencies from `requirements.txt`.

## Setup

With `mise`:

```sh
mise install
mise run install
```

Or directly with `uv`:

```sh
uv sync
```

If you are not using `uv`, install the requirements into your active virtual environment:

```sh
pip install -r requirements.txt
```

## Run The API

With `mise`:

```sh
mise run dev
```

Or directly:

```sh
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## API

### Health Check

```sh
curl http://localhost:8000/healthz
```

Response:

```json
{"status":"ok"}
```

### Create A Job

```sh
curl -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"generate a product photo"}'
```

Jobs start as `IN_QUEUE`. The background worker then moves them through `IN_PROGRESS` to `COMPLETED` after the simulated inference delay.

### Get A Job

```sh
curl http://localhost:8000/jobs/<job_id>
```

### List Jobs

```sh
curl http://localhost:8000/jobs
```

### Cancel A Job

```sh
curl -X POST http://localhost:8000/jobs/<job_id>/cancel
```

Jobs can be cancelled unless they are already `COMPLETED`, `FAILED`, or `CANCELLED`.

### Manually Process A Job

```sh
curl -X POST http://localhost:8000/jobs/<job_id>/process
```

This endpoint processes a queued job immediately in the request path. The background worker also processes queued jobs automatically, so this endpoint is mainly useful for exercises and direct API testing.

## Job Model

Jobs have the following fields:

- `id`: UUID string
- `prompt`: submitted prompt text
- `status`: one of `IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, or `CANCELLED`
- `created_at`: UTC creation timestamp
- `updated_at`: UTC last-update timestamp
- `result`: generated result text, present after completion
- `optional`: currently unused optional field

## Development

Run tests:

```sh
mise run test
```

Or:

```sh
uv run pytest
```

Run linting:

```sh
mise run lint
```

Or:

```sh
uv run ruff check .
```

## Notes

- Jobs are stored in process memory. They are lost when the server restarts.
- The queue has a single background worker.
- `fake_model_inference` sleeps for three seconds and returns a deterministic placeholder result.
- This is an interview-prep exercise, not a production queue implementation.
