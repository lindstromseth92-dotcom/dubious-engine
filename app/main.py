import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app import db
from dubious.pipeline import run

load_dotenv()
app = FastAPI(title="Dubious Engine", version="0.2.0")
conn = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
queue = Queue("default", connection=conn)


class CheckRequest(BaseModel):
    source: str = Field(description="A URL or a block of text")


class FeedbackRequest(BaseModel):
    check_id: str
    claim_index: int
    vote: str = Field(pattern="^(up|down)$")
    note: str | None = None


@app.get("/health")  # not /healthz: Cloud Run reserves paths ending in z
def health():
    return {"ok": True}


@app.post("/check", status_code=202)
def check(req: CheckRequest):
    job = queue.enqueue(run, req.source, result_ttl=3600)
    return {"check_id": job.id, "status": "queued"}


@app.get("/check/{check_id}")
def check_status(check_id: str):
    try:
        job = Job.fetch(check_id, connection=conn)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="unknown check_id") from None
    status = job.get_status().value
    body = {"check_id": check_id, "status": status}
    if status == "finished":
        body["result"] = job.return_value()
    elif status == "failed":
        body["error"] = "check failed; see worker logs"
    return body


@app.post("/feedback", status_code=201)
def feedback(req: FeedbackRequest):
    db.save_feedback(req.check_id, req.claim_index, req.vote, req.note)
    return {"ok": True}


@app.get("/stats")
def get_stats():
    return db.stats()