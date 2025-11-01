from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis
from rq import Queue, Retry
import hashlib
import os

app = FastAPI(title="Jobs API")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# RQ prefers a Redis connection object. Parse from REDIS_URL if needed.
# Simple: let redis-py parse URL via from_url
_redis = Redis.from_url(REDIS_URL)
q = Queue("tts", connection=_redis)

class TTSJobIn(BaseModel):
    text: str
    speaker: str = "peter"
    preset: str = "ultra_fast"

class JobEnqueued(BaseModel):
    job_id: str
    status: str


def _idem_key(text: str, speaker: str, preset: str) -> str:
    h = hashlib.sha256(f"{text}|{speaker}|{preset}".encode()).hexdigest()
    # RQ disallows ':' in job IDs; use '-' delimiter
    return f"tts-{h}"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/jobs/tts", response_model=JobEnqueued)
def enqueue_tts(body: TTSJobIn):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text required")
    job_id = _idem_key(body.text, body.speaker, body.preset)
    # Enqueue if not already present or finished; allow redo via same id (RQ stores last result)
    job = q.enqueue(
        "worker_tasks.tts_task",
        body.text,
        body.speaker,
        job_id=job_id,
        retry=Retry(max=3),
        result_ttl=24*3600,
    )
    return JobEnqueued(job_id=job.get_id(), status=job.get_status())

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=_redis)
    except Exception:
        raise HTTPException(status_code=404, detail="job not found")
    status = job.get_status()
    if status == "finished":
        return {"status": status, "result": job.result}
    if status == "failed":
        return {"status": status, "error": str(job.exc_info)}
    return {"status": status}
