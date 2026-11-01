from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import db
from dubious.pipeline import run

load_dotenv()
app = FastAPI(title="Dubious Engine", version="0.1.0")


class CheckRequest(BaseModel):
    source: str = Field(description="A URL or a block of text")


class FeedbackRequest(BaseModel):
    check_id: str
    claim_index: int
    vote: str = Field(pattern="^(up|down)$")
    note: str | None = None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/check")
def check(req: CheckRequest):
    try:
        result = run(req.source)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    result["check_id"] = db.save_check(result)
    return result


@app.post("/feedback", status_code=201)
def feedback(req: FeedbackRequest):
    db.save_feedback(req.check_id, req.claim_index, req.vote, req.note)
    return {"ok": True}


@app.get("/stats")
def get_stats():
    return db.stats()