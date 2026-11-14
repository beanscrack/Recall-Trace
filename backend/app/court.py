"""RecallTrace: verdict proposal and human approval. See brief section 8.

The model only drafts. Nothing changes in memories until a human approves.
"""
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import OperationFailure

from . import db
from .db import EVIDENCE_INDEX
from .embeddings import embed
from .errors import Conflict
from .llm import propose_correction


def _now():
    return datetime.now(timezone.utc)


def find_evidence(memory: dict) -> dict | None:
    """Verified, newer, and about the same thing: a lookup, not a model judgment.

    Require explicit service metadata, the same tenant/service, a newer date,
    and a nonblank verifier. If the vector index is unavailable, use exactly
    those eligibility rules in the normal-query fallback. Untagged legacy
    memories cannot be matched safely and receive no corrective evidence.
    """
    service = memory.get("service")
    if not isinstance(service, str) or not service.strip():
        return None
    newer = {"tenant_id": memory["tenant_id"], "service": service,
             "created_at": {"$gt": memory["created_at"]},
             "verified_by": {"$type": "string", "$regex": r"\S"}}
    try:
        has_index = any(i["name"] == EVIDENCE_INDEX and i.get("queryable", False)
                        for i in db.evidence().list_search_indexes())
    except OperationFailure as exc:
        if exc.code not in (26, 27):  # absent namespace/index, not an authentication or server failure
            raise
        has_index = False
    if has_index and memory.get("embedding"):
        pipeline = [
            {"$vectorSearch": {
                "index": EVIDENCE_INDEX, "path": "embedding", "queryVector": memory["embedding"],
                "numCandidates": 50, "limit": 5,
                "filter": {"tenant_id": {"$eq": memory["tenant_id"]}},
            }},
            {"$set": {"score": {"$meta": "vectorSearchScore"}}},
            {"$match": newer},  # service/date/verifier need not be vector-index filter fields
            {"$limit": 1},
            {"$unset": "embedding"},
        ]
        try:
            hit = next(db.evidence().aggregate(pipeline), None)
        except OperationFailure as exc:
            if exc.code not in (26, 27):
                raise
            hit = None
        if hit:
            return hit
    return db.evidence().find_one(newer, {"embedding": 0}, sort=[("created_at", -1)])


def propose_verdict(decision_id: str) -> dict:
    d = db.decisions().find_one({"_id": ObjectId(decision_id)})
    if not d:
        raise Conflict("decision not found")
    rep = db.replays().find_one({"decision_id": d["_id"]}, sort=[("created_at", -1)])
    if not rep:
        raise Conflict("run the replay before proposing a verdict")
    # Don't redraft on a repeated click; scoped to the latest replay so a re-replay gets a fresh verdict.
    existing = db.verdicts().find_one({"decision_id": d["_id"], "replay_id": rep["_id"],
                                       "status": {"$ne": "rejected"}}, sort=[("_id", -1)])
    if existing:
        return existing

    v = {"decision_id": d["_id"], "replay_id": rep["_id"], "memory_id": rep.get("culprit_memory_id"),
         "evidence_id": None, "outcome": "no_action", "reason": "", "proposed_text": None,
         "status": "proposed", "approved_by": None, "approved_at": None, "new_memory_id": None,
         # display snapshots for the verdict panel (additive to brief section 6)
         "memory_text": None, "evidence_title": None, "evidence_text": None, "evidence_verified_by": None}

    mem = v["memory_id"] and db.memories().find_one({"_id": v["memory_id"], "tenant_id": d["tenant_id"]})
    if not rep.get("stable", True):
        v["reason"] = (f"Baseline was unstable (stability {rep['baseline']['stability']:.0%}), so no memory can be "
                       "blamed. Rerun the replay.")
    elif not v["memory_id"]:
        v["reason"] = "Black Box found no memory whose removal flips the decision at least 2/3 of the time."
    elif not mem or mem["status"] != "active":
        v["reason"] = "The culprit memory is no longer active; nothing to correct."
    else:
        v["memory_text"] = mem["text"]
        flip = next((a["flip_rate"] for a in rep["ablations"] if a["removed_memory_id"] == mem["_id"]), None)
        ev = find_evidence(mem)
        if not ev:
            v["outcome"] = "quarantine"
            v["reason"] = (f"Removing this memory flips the decision {flip:.0%} of the time, and no newer "
                           "verified evidence exists to correct it against.")
        else:
            v.update(evidence_id=ev["_id"], evidence_title=ev["title"], evidence_text=ev["text"],
                     evidence_verified_by=ev.get("verified_by"))
            review = propose_correction(mem["text"], ev["text"], d["model"])
            v["reason"] = review["reason"]
            if review["contradicts"]:
                v["outcome"], v["proposed_text"] = "correct", review["corrected_text"]

    v["_id"] = db.verdicts().insert_one(v).inserted_id
    return v


def approve_verdict(verdict_id: str, approved_by: str) -> dict:
    v = db.verdicts().find_one({"_id": ObjectId(verdict_id)})
    if not v:
        raise Conflict("verdict not found")
    if v["status"] != "proposed":
        raise Conflict(f"verdict is already {v['status']}")

    if v["outcome"] in ("correct", "quarantine"):
        old = db.memories().find_one({"_id": v["memory_id"]})
        if not old or old["status"] != "active":
            raise Conflict("memory is no longer active")
        new = None
        if v["outcome"] == "correct":  # embed before any write so a Voyage failure changes nothing
            new = {
                "tenant_id": old["tenant_id"], "text": v["proposed_text"],
                "service": old.get("service"),
                "embedding": embed([v["proposed_text"]])[0], "status": "active",
                "version": old["version"] + 1, "supersedes": old["_id"], "superseded_by": None,
                "source": "court_correction", "source_evidence_id": v["evidence_id"],
                "created_by": f"court:approved-by:{approved_by}", "created_at": _now(),
                "expires_at": old["expires_at"],
            }
    else:
        old = new = None

    update = {"status": "approved", "approved_by": approved_by, "approved_at": _now()}

    def write(session):
        # One transaction: quarantine, insert the new version, link it, approve. All or nothing.
        new_id = None
        if old:
            res = db.memories().update_one({"_id": old["_id"], "status": "active"},
                                           {"$set": {"status": "quarantined"}}, session=session)
            if res.modified_count != 1:
                raise Conflict("memory is no longer active")
        if new:
            new_id = db.memories().insert_one(dict(new), session=session).inserted_id
            db.memories().update_one({"_id": old["_id"]}, {"$set": {"superseded_by": new_id}}, session=session)
        res = db.verdicts().update_one({"_id": v["_id"], "status": "proposed"},
                                       {"$set": {**update, "new_memory_id": new_id}}, session=session)
        if res.modified_count != 1:
            raise Conflict("verdict is no longer proposed")
        return new_id

    with db.get_db().client.start_session() as session:
        update["new_memory_id"] = session.with_transaction(write)
    v.update(update)
    return v
