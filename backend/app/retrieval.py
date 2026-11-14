"""The only code path that reads memories for the agent.

tenant_id comes from the session (route handler), never from the model.
"""
from datetime import datetime, timezone

from bson import ObjectId

from . import db
from .db import MEMORY_INDEX
from .embeddings import embed_query


def _log(tenant_id, user_id, kind, query, returned_ids, allowed):
    db.access_log().insert_one({
        "tenant_id": tenant_id, "user_id": user_id, "kind": kind, "query": query,
        "returned_ids": returned_ids, "allowed": allowed, "at": datetime.now(timezone.utc),
    })


def search_memories(tenant_id: str, user_id: str, query: str, k: int = 4) -> list[dict]:
    now = datetime.now(timezone.utc)
    pipeline = [
        {"$vectorSearch": {
            "index": MEMORY_INDEX,
            "path": "embedding",
            "queryVector": embed_query(query),
            "numCandidates": 100,
            "limit": k + 4,  # headroom for the live re-check below; trimmed to k after it
            "filter": {"$and": [
                {"tenant_id": {"$eq": tenant_id}},
                {"status": {"$eq": "active"}},
                {"expires_at": {"$gt": now}},
            ]},
        }},
        {"$set": {"score": {"$meta": "vectorSearchScore"}}},
        # Re-check live fields: the search index lags writes by ~1s, so a just-quarantined memory could
        # otherwise still match the pre-filter above.
        {"$match": {"tenant_id": tenant_id, "status": "active", "expires_at": {"$gt": now}}},
        {"$limit": k},
        {"$unset": "embedding"},
    ]
    docs = list(db.memories().aggregate(pipeline))
    _log(tenant_id, user_id, "search", query, [d["_id"] for d in docs], True)
    return docs


def get_memory(tenant_id: str, user_id: str, memory_id: str) -> dict | None:
    """Direct read. Returns None (and logs a refusal) for another tenant's memory."""
    try:
        oid = ObjectId(memory_id)
    except Exception:
        return None
    doc = db.memories().find_one({"_id": oid}, {"embedding": 0})
    allowed = doc is not None and doc["tenant_id"] == tenant_id
    _log(tenant_id, user_id, "get", memory_id, [oid] if allowed else [], allowed)
    return doc if allowed else None
