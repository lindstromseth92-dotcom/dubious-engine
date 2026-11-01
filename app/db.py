import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path("dubious.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
  id TEXT PRIMARY KEY, ts TEXT, source TEXT, model TEXT,
  tokens_in INT, tokens_out INT, cost_usd REAL, latency_s REAL, n_claims INT, result TEXT);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, check_id TEXT, claim_index INT,
  vote TEXT CHECK(vote IN ('up','down')), note TEXT);
"""


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    return c


def now() -> str:
    return datetime.now(UTC).isoformat()


def save_check(result: dict) -> str:
    cid, m = str(uuid.uuid4()), result["meta"]
    with conn() as c:
        c.execute(
            "INSERT INTO checks VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, now(), result["source"], m["model"], m["tokens_in"], m["tokens_out"],
             m["cost_usd"], m["latency_s"], len(result["claims"]), json.dumps(result)),
        )
    return cid


def save_feedback(check_id: str, claim_index: int, vote: str, note: str | None) -> None:
    with conn() as c:
        c.execute("INSERT INTO feedback (ts, check_id, claim_index, vote, note) VALUES (?,?,?,?,?)",
                  (now(), check_id, claim_index, vote, note))


def stats() -> dict:
    with conn() as c:
        checks, claims, cost, lat = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(n_claims),0), COALESCE(SUM(cost_usd),0), COALESCE(AVG(latency_s),0) FROM checks"
        ).fetchone()
        up, down = c.execute(
            "SELECT SUM(vote='up'), SUM(vote='down') FROM feedback"
        ).fetchone()
    up, down = up or 0, down or 0
    return {
        "checks": checks, "claims": claims, "total_cost_usd": round(cost, 4),
        "cost_per_claim_usd": round(cost / claims, 6) if claims else None,
        "avg_latency_s": round(lat, 2),
        "feedback": {"up": up, "down": down,
                     "agreement": round(up / (up + down), 2) if up + down else None},
    }