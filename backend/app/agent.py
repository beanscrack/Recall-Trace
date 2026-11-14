"""run_task: retrieve -> decide -> act on the simulation -> record."""
from datetime import datetime, timezone

from . import db, sim
from .llm import decide, default_model
from .prompts import SYSTEM_PROMPT, TOOLS
from .retrieval import search_memories


def run_task(session: dict, task: str, rerun_of=None) -> dict:
    """session = {user_id, tenant_id}, built by the route handler."""
    docs = search_memories(session["tenant_id"], session["user_id"], task)
    retrieved = [{"memory_id": d["_id"], "version": d["version"], "score": d["score"], "text": d["text"]}
                 for d in docs]
    model = default_model()
    prompt_memories = [{"memory_id": str(r["memory_id"]), "text": r["text"]} for r in retrieved]
    result = decide(SYSTEM_PROMPT, task, prompt_memories, TOOLS, model)

    sim_before = sim.get()
    sim_after = sim.apply(result["action"])
    doc = {
        "tenant_id": session["tenant_id"], "user_id": session["user_id"], "task": task,
        "system_prompt": SYSTEM_PROMPT, "model": model, "tools": TOOLS, "retrieved": retrieved,
        "action": result["action"], "action_args": result["action_args"], "rationale": result["rationale"],
        "sim_before": sim_before, "sim_after": sim_after, "contested": None, "rerun_of": rerun_of,
        "created_at": datetime.now(timezone.utc),
    }
    doc["_id"] = db.decisions().insert_one(doc).inserted_id
    return doc
