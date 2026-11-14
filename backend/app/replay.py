"""Black Box: counterfactual replay of a recorded decision. See brief section 8.

Reads only the stored decisions document; never re-queries memories, never touches the sim.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from bson import ObjectId

from . import db
from .errors import Conflict
from .llm import decide

RUNS_PER_VARIANT = 3
THRESHOLD = 2 / 3


def _prompt_memories(retrieved: list[dict], skip=None) -> list[dict]:
    # Same layout agent.run_task used for the live call, minus the removed memory.
    return [{"memory_id": str(r["memory_id"]), "text": r["text"]} for r in retrieved if r["memory_id"] != skip]


def run_replay(decision_id: str) -> dict:
    d = db.decisions().find_one({"_id": ObjectId(decision_id)})
    if not d:
        raise Conflict("decision not found")
    original, retrieved, n = d["action"], d["retrieved"], RUNS_PER_VARIANT

    # Variant None is the baseline; otherwise the memory_id removed. All calls run concurrently.
    variants = [None] + [r["memory_id"] for r in retrieved]
    jobs = [(v, i) for v in variants for i in range(n)]

    def call(job):
        mems = _prompt_memories(retrieved, skip=job[0])
        return decide(d["system_prompt"], d["task"], mems, d["tools"], d["model"])["action"]

    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        actions = list(ex.map(call, jobs))
    by_variant = {v: actions[k * n:(k + 1) * n] for k, v in enumerate(variants)}

    base = by_variant[None]
    stability = sum(a == original for a in base) / n
    stable = stability >= THRESHOLD
    ablations, culprit = [], None
    if stable:  # below 2/3 the flip rates are meaningless, so report only the baseline
        for r in retrieved:
            acts = by_variant[r["memory_id"]]
            ablations.append({"removed_memory_id": r["memory_id"], "actions": acts,
                              "flip_rate": sum(a != original for a in acts) / n})
        top = max(ablations, key=lambda a: a["flip_rate"], default=None)
        if top and top["flip_rate"] >= THRESHOLD:
            culprit = top["removed_memory_id"]

    doc = {
        "decision_id": d["_id"], "runs_per_variant": n, "original_action": original,
        "baseline": {"actions": base, "stability": stability}, "stable": stable,
        "ablations": ablations, "culprit_memory_id": culprit, "created_at": datetime.now(timezone.utc),
    }
    doc["_id"] = db.replays().insert_one(doc).inserted_id
    return doc
