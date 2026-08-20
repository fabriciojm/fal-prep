import asyncio
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from datetime import UTC, datetime

import httpx
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://guama:8000")


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    prompt: str
    status: JobStatus = JobStatus.PENDING
    image_url: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateJobRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)


class InferenceRunner:
    def __init__(self, base_url: str):
        self.endpoint = f"{base_url}/generate"

    async def run(self, prompt: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json={
                    "prompt": prompt,
                },
                timeout=120,
            )

        response.raise_for_status()

        data = response.json()

        return data


class JobService:
    def __init__(self, runner: InferenceRunner):
        self.runner = runner
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def now(self) -> datetime:
        return datetime.now(UTC)

    async def submit_job(self, prompt: str) -> Job:
        timestamp = self.now()

        job = Job(
            id=str(uuid.uuid4()),
            prompt=prompt,
            status=JobStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.jobs[job.id] = job
        await self.queue.put(job.id)

        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        return list(self.jobs.values())

    async def process_job(self, job_id: str) -> None:
        job = self.jobs.get(job_id)

        if job is None:
            return

        job.status = JobStatus.PROCESSING
        job.updated_at = self.now()

        try:
            result = await self.runner.run(job.prompt)

            if result["success"]:
                job.status = JobStatus.COMPLETED
                job.image_url = f"/images/{result['image_id']}"
                job.error = None
            else:
                job.status = JobStatus.FAILED
                job.error = result.get("error", result.get("message"))

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)

        finally:
            job.updated_at = self.now()

    async def worker_loop(self) -> None:
        while True:
            job_id = await self.queue.get()

            try:
                await self.process_job(job_id)
            finally:
                self.queue.task_done()


runner = InferenceRunner(INFERENCE_SERVICE_URL)
job_service = JobService(runner)


# HTTP layer
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(job_service.worker_loop())
    try:
        yield
    # Shutdown code
    finally:
        worker_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs")
async def create_job(request: CreateJobRequest) -> Job:
    return await job_service.submit_job(request.prompt)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Job:
    job = job_service.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.get("/jobs")
async def list_jobs() -> list[Job]:
    return job_service.list_jobs()


@app.get("/status")
async def status() -> dict:
    return {
        "queue_size": job_service.queue.qsize(),
        "jobs_total": len(job_service.jobs),
    }


@app.get("/images/{image_id}")
async def get_image(image_id: str):
    image_url = f"{INFERENCE_SERVICE_URL}/images/{image_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(image_url)

    if response.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail="image not found",
        )

    return StreamingResponse(
        iter([response.content]),
        media_type="image/png",
    )


async def main() -> None:
    job = await job_service.submit_job("A GPU serverless platform")

    print(job)
    print(job_service.get_job(job.id))
    print(job_service.queue.qsize())


if __name__ == "__main__":
    asyncio.run(main())
