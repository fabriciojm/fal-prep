from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import asyncio
from asyncio import Queue
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class JobStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)


class Job(BaseModel):
    id: str
    prompt: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: str | None = None
    optional: str | None = None


async def fake_model_inference(prompt: str) -> str:
    await asyncio.sleep(3)
    return f"Generated result for prompt: {prompt}"


async def worker_loop() -> None:
    while True:
        job_id = await job_queue.get()

        try:
            job = jobs.get(job_id)

            if job is None:
                continue

            if job.status != JobStatus.IN_QUEUE:
                continue

            running = job.model_copy(
                update={
                    "status": JobStatus.IN_PROGRESS,
                    "updated_at": now_utc(),
                }
            )
            jobs[job_id] = running

            result = await fake_model_inference(running.prompt)

            completed = running.model_copy(
                update={
                    "status": JobStatus.COMPLETED,
                    "updated_at": now_utc(),
                    "result": result,
                }
            )
            jobs[job_id] = completed

        except Exception as exc:
            job = jobs.get(job_id)

            if job is not None:
                failed = job.model_copy(
                    update={
                        "status": JobStatus.FAILED,
                        "updated_at": now_utc(),
                        "error": str(exc),
                    }
                )
                jobs[job_id] = failed

        finally:
            job_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    worker_task = asyncio.create_task(worker_loop())

    try:
        yield
    finally:
        worker_task.cancel()


app = FastAPI(title="Mini fal.ai Queue", lifespan=lifespan)

jobs: dict[str, Job] = {}
job_queue: Queue[str] = Queue()

def now_utc() -> datetime:
    return datetime.now(UTC)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/jobs", response_model=Job)
async def create_job(payload: JobCreate) -> Job:
    job_id = str(uuid4())
    timestamp = now_utc()

    job = Job(
        id=job_id,
        prompt=payload.prompt,
        status=JobStatus.IN_QUEUE,
        created_at=timestamp,
        updated_at=timestamp,
    )

    jobs[job_id] = job
    await job_queue.put(job_id)

    return job

@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.get("/jobs", response_model=list[Job])
def list_jobs() -> list[Job]:
    return list(jobs.values())


@app.post("/jobs/{job_id}/cancel", response_model=Job)
def cancel_job(job_id: str) -> Job:
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status {job.status}",
        )
    updated = job.model_copy(
        update={
            "status": JobStatus.CANCELLED,
            "updated_at": now_utc(),
        }
    )
    jobs[job_id] = updated
    return updated


@app.post("/jobs/{job_id}/process", response_model=Job)
def process_job(job_id: str) -> Job:
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.IN_QUEUE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process job with status {job.status}",
        )

    running = job.model_copy(
        update={
            "status": JobStatus.IN_PROGRESS,
            "updated_at": now_utc(),
        }
    )

    jobs[job_id] = running

    completed = running.model_copy(
        update={
            "status": JobStatus.COMPLETED,
            "updated_at": now_utc(),
            "result": f"Generated result for prompt {running.prompt}",
        }
    )

    jobs[job_id] = completed

    return completed

