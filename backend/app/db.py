"""Mongo client, collection handles, index and validator setup.

Only touches the MONGODB_DB database.
"""
import time
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.operations import SearchIndexModel

from . import config

COLLECTIONS = ["memories", "evidence", "decisions", "replays", "verdicts", "access_log"]
MEMORY_INDEX = "memory_vector_index"
EVIDENCE_INDEX = "evidence_vector_index"


@lru_cache
def get_db() -> Database:
    if not config.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set (see .env.example)")
    return MongoClient(config.MONGODB_URI, appname="memory-court")[config.MONGODB_DB]


def memories():
    return get_db().memories


def evidence():
    return get_db().evidence


def decisions():
    return get_db().decisions


def replays():
    return get_db().replays


def verdicts():
    return get_db().verdicts


def access_log():
    return get_db().access_log


MEMORY_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["tenant_id", "text", "status", "version", "created_at", "expires_at"],
        "properties": {
            "tenant_id": {"bsonType": "string", "minLength": 1},
            "text": {"bsonType": "string"},
            "status": {"enum": ["active", "quarantined"]},
            "version": {"bsonType": "int", "minimum": 1},
            "created_at": {"bsonType": "date"},
            "expires_at": {"bsonType": "date"},
        },
    }
}


def ensure_collections() -> None:
    db = get_db()
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            db.create_collection(name)
    db.command("collMod", "memories", validator=MEMORY_VALIDATOR, validationLevel="strict")


def _vector_index(name: str, filters: list[str]) -> SearchIndexModel:
    fields = [{"type": "vector", "path": "embedding",
               "numDimensions": config.EMBEDDING_DIM, "similarity": "cosine"}]
    fields += [{"type": "filter", "path": p} for p in filters]
    return SearchIndexModel(name=name, type="vectorSearch", definition={"fields": fields})


def ensure_indexes() -> dict:
    """Create both vector indexes if missing. Returns {index_name: 'created'|'exists'|error}."""
    db = get_db()
    wanted = {
        "memories": _vector_index(MEMORY_INDEX, ["tenant_id", "status", "expires_at"]),
        "evidence": _vector_index(EVIDENCE_INDEX, ["tenant_id"]),
    }
    result = {}
    for coll, model in wanted.items():
        name = model.document["name"]
        names = {i["name"] for i in db[coll].list_search_indexes()}
        if name in names:
            result[name] = "exists"
            continue
        try:
            db[coll].create_search_index(model=model)
            result[name] = "created"
        except Exception as e:  # sandbox may cap the number of search indexes
            result[name] = f"error: {e}"
    return result


def index_status() -> dict:
    db = get_db()
    out = {}
    for coll, name in [("memories", MEMORY_INDEX), ("evidence", EVIDENCE_INDEX)]:
        info = next((i for i in db[coll].list_search_indexes(name)), None)
        out[name] = None if info is None else {"status": info.get("status"), "queryable": info.get("queryable")}
    return out


def wait_queryable(name: str = MEMORY_INDEX, coll: str = "memories", timeout: int = 300) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = next((i for i in get_db()[coll].list_search_indexes(name)), None)
        if info and info.get("queryable"):
            return True
        time.sleep(5)
    return False
