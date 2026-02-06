import os
from arq.connections import RedisSettings
from worker.tasks import generate_and_send

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

ARQ_QUEUE = os.getenv("ARQ_QUEUE", "q:gemini_2_5_image")

class WorkerSettings:
    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT, database=REDIS_DB)
    functions = [generate_and_send]

    # This worker listens to one queue (best for per-model scaling)
    queue_name = ARQ_QUEUE

    # local concurrency inside one process (jobs in parallel)
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "50"))

    # job timeout fallback (seconds)
    job_timeout = int(os.getenv("ARQ_JOB_TIMEOUT", "900"))

    retry_jobs = True
