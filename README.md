# laf-api

Small FastAPI api for providing image generation (like fal.ai). Look at the last generations [here](https://laf.fabriciojm.com)

This repo currently implements a minimal in-memory job queue API. Clients submit prompt jobs, a background worker calls a model inference runner, and the API exposes endpoints for checking/handling jobs. The model inference runner calls a container specified in [laf-inference](https://github.com/fabriciojm/laf-inference).

This service (api+inference+dashboard) is currently running in [my homelab](https://github.com/fabriciojm/homelab) kubernetes cluster. Follow that link if you want to see the kubernetes manfests used (under `apps/`).

The API is not public, but what I generate can be seen in [the dashboard](https://laf.fabriciojm.com) ([repo](https://github.com/fabriciojm/laf-dashboard)).

The API be can run using the image provided in packages, e.g. by using the docker compose file in the repo.

## Some API endpoints

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

### Get A Job

```sh
curl http://localhost:8000/jobs/<job_id>
```

### List Jobs

```sh
curl http://localhost:8000/jobs
```

## Job Model

Jobs have the following fields:

- `id`: UUID string
- `prompt`: submitted prompt text
- `status`: one of `PENDING`, `PROCESSING`, `COMPLETED` or `FAILED`
- `created_at`/`updated_at`: UTC timestamps
- `image_url`: url that can e.g. be called from the dashboaed
- `error`: error message from the inference worker, if any

## Notes

- This is a draft of the documentation, many details of the code are not described here.
