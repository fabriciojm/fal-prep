from contextlib import asynccontextmanager
from enum import Enum

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

# I'll write a Job class, a JobStatus class, CreateJobRequest
# Have a fake runner (async)
# I'll have a JobService that will have
#  - async submit_job -> create and enqueue job
#  - get_job -> poll jobs
#  - async process_job -> process single job id
#  - async worker_loop -> waits for jobs and processes them
# I'll write a thin http layer
#


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    prompt: str
    status: JobStatus = JobStatus.PENDING
    result: str | None = None
    error: str | None = None


class CreateJobRequest(BaseModel):
    prompt: str


class FakeRunner:
    async def run(self, prompt: str) -> str:
        await asyncio.sleep(3)

        if "fail" in prompt.lower():
            raise RuntimeError("fake runner failure")

        return f"Generated result for prompt: {prompt}"


class JobService:
    def __init__(self, runner: FakeRunner):
        self.runner = runner
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    async def submit_job(self, prompt: str) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            prompt=prompt,
        )
        self.jobs[job.id] = job
        await self.queue.put(job.id)

        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def process_job(self, job_id: str) -> None:
        job = self.jobs.get(job_id)

        if job is None:
            return

        job.status = JobStatus.PROCESSING

        try:
            result = await self.runner.run(job.prompt)

            job.result = result
            job.status = JobStatus.COMPLETED

        except Exception as exc:
            job.error = str(exc)
            job.status = JobStatus.FAILED

    async def worker_loop(self) -> None:
        while True:
            job_id = await self.queue.get()

            try:
                await self.process_job(job_id)
            finally:
                self.queue.task_done()


runner = FakeRunner()
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


# Two methods: POST to submit a job and GET to poll the job store
#
@app.post("/jobs")
async def create_job(request: CreateJobRequest) -> Job:
    return await job_service.submit_job(request.prompt)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Job:
    job = job_service.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


async def main() -> None:
    job = await job_service.submit_job("A GPU serverless platform")

    print(job)
    print(job_service.get_job(job.id))
    print(job_service.queue.qsize())


if __name__ == "__main__":
    asyncio.run(main())

