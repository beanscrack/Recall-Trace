"""FastAPI routes. Session user comes from the X-User header; tenant is mapped server-side."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import agent, config, court, db, replay, seed, sim
from .errors import Conflict
from .retrieval import get_memory

app = FastAPI(title="Memory Court")
ENC = {ObjectId: str}


@app.exception_handler(Conflict)
def conflict(_request, exc: Conflict):  # replay/court precondition failures -> 409, not 500
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def out(obj):
    return jsonable_encoder(obj, custom_encoder=ENC)


def session(x_user: str = Header(...)) -> dict:
    tenant = config.USERS.get(x_user)
    if not tenant:
        raise HTTPException(401, f"unknown user {x_user}")
    return {"user_id": x_user, "tenant_id": tenant}


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(404, "not found")


def _own_decision(decision_id: str, s: dict) -> dict:
    d = db.decisions().find_one({"_id": _oid(decision_id), "tenant_id": s["tenant_id"]})
    if not d:
        raise HTTPException(404, "not found")
    return d


class RunBody(BaseModel):
    task: str
    rerun_of: str | None = None


class ContestBody(BaseModel):
    reason: str = ""


@app.get("/api/health")
def health():
    return out({"ok": True, "db": config.MONGODB_DB, "indexes": db.index_status()})


@app.get("/api/users")
def users():
    return config.USERS


@app.post("/api/run")
def run(body: RunBody, s=Depends(session)):
    rerun_of = _own_decision(body.rerun_of, s)["_id"] if body.rerun_of else None
    return out(agent.run_task(s, body.task, rerun_of))


@app.get("/api/decisions/{decision_id}")
def get_decision(decision_id: str, s=Depends(session)):
    d = _own_decision(decision_id, s)
    d["replay"] = db.replays().find_one({"decision_id": d["_id"]}, sort=[("created_at", -1)])
    d["verdict"] = db.verdicts().find_one({"decision_id": d["_id"]}, sort=[("_id", -1)])
    return out(d)


@app.post("/api/decisions/{decision_id}/contest")
def contest(decision_id: str, body: ContestBody, s=Depends(session)):
    d = _own_decision(decision_id, s)
    contested = {"by": s["user_id"], "reason": body.reason, "at": datetime.now(timezone.utc)}
    db.decisions().update_one({"_id": d["_id"]}, {"$set": {"contested": contested}})
    return out(contested)


@app.post("/api/decisions/{decision_id}/replay")
def run_replay(decision_id: str, s=Depends(session)):
    _own_decision(decision_id, s)
    return out(replay.run_replay(decision_id))


@app.post("/api/decisions/{decision_id}/verdict")
def verdict(decision_id: str, s=Depends(session)):
    _own_decision(decision_id, s)
    return out(court.propose_verdict(decision_id))


@app.post("/api/verdicts/{verdict_id}/approve")
def approve(verdict_id: str, s=Depends(session)):
    v = db.verdicts().find_one({"_id": _oid(verdict_id)})
    if not v or not db.decisions().find_one({"_id": v["decision_id"], "tenant_id": s["tenant_id"]}):
        raise HTTPException(404, "not found")
    return out(court.approve_verdict(verdict_id, s["user_id"]))


@app.get("/api/memories")
def list_memories(s=Depends(session)):
    return out(list(db.memories().find({"tenant_id": s["tenant_id"]}, {"embedding": 0}).sort("created_at", 1)))


@app.get("/api/memories/{memory_id}")
def read_memory(memory_id: str, s=Depends(session)):
    doc = get_memory(s["tenant_id"], s["user_id"], memory_id)
    if not doc:
        raise HTTPException(404, "not found")
    return out(doc)


@app.get("/api/access-log")
def access_log(s=Depends(session)):
    return out(list(db.access_log().find({"tenant_id": s["tenant_id"]}).sort("at", -1).limit(50)))


@app.get("/api/sim")
def get_sim():
    return sim.get()


@app.post("/api/sim/reset")
def reset_sim():
    return sim.reset()


@app.post("/api/demo/reset")
def demo_reset():
    return seed.reset()
