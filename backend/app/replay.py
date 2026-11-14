"""Black Box: counterfactual replay of a recorded decision. See brief section 8.

Reads only the stored decisions document; never re-queries memories, never touches the sim.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from itertools import combinations

from bson import ObjectId

from . import db, llm
from .errors import Conflict

RUNS_PER_VARIANT = 3
THRESHOLD = 2 / 3
MAX_WORKERS = 15


def run_replay(decision_id: str, include_pairs: bool = False) -> dict:
    """Replay recorded inputs only; the API checks decision ownership before calling.

    Rates use all N scheduled trials as the denominator. Failed requests occupy a
    null action slot and never count as flips. Any failure prevents attribution,
    so partial results cannot masquerade as a complete influence comparison.
    A tied highest flip rate also leaves culprit_memory_id unset.
    """
    decision = db.decisions().find_one({"_id": ObjectId(decision_id)})
    if decision is None:
        raise Conflict("Decision not found")

    if include_pairs and not 2 <= len(decision["retrieved"]) <= 4:
        raise Conflict("Pair investigation supports snapshots with 2 to 4 memories")

    # Match agent.run_task's input transformation exactly, including ID strings.
    memories = [{"memory_id": str(m["memory_id"]), "text": m["text"]}
                for m in decision["retrieved"]]
    allowed_actions = {t["name"] for t in decision["tools"]}
    original_action = decision["action"]
    if original_action not in allowed_actions:
        raise Conflict("Recorded action is absent from recorded tools")

    def trial(variant):
        try:
            result = llm.decide(
                decision["system_prompt"], decision["task"], deepcopy(variant),
                deepcopy(decision["tools"]), deepcopy(decision["model"]),
            )
            action = result["action"]
            if not isinstance(action, str) or action not in allowed_actions:
                raise ValueError("Invalid tool action")
            return action, None
        except Exception as exc:
            # Provider messages may contain credentials or prompt contents.
            return None, type(exc).__name__

    def summarize(results):
        return {
            "actions": [action for action, _ in results],
            "errors": [{"run": i + 1, "type": error}
                       for i, (_, error) in enumerate(results) if error],
        }

    doc = {
        "decision_id": decision["_id"], "tenant_id": decision["tenant_id"],
        "runs_per_variant": RUNS_PER_VARIANT, "baseline": {}, "ablations": [],
        "culprit_memory_id": None, "original_action": original_action, "stable": False,
    }
    if include_pairs:
        doc["pairs"] = {"status": "not_run", "selection": "all_pairs", "ablations": [], "candidate_memory_ids": []}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        baseline = summarize(list(executor.map(trial, [memories] * RUNS_PER_VARIANT)))
        baseline["stability"] = baseline["actions"].count(original_action) / RUNS_PER_VARIANT
        doc["baseline"] = baseline
        doc["stable"] = not baseline["errors"] and baseline["stability"] >= THRESHOLD
        if baseline["errors"]:
            doc["status"] = "incomplete"
        elif baseline["stability"] < THRESHOLD:
            doc["status"] = "unstable_baseline"
        else:
            # Submit every ablation before collecting results; keep snapshot order.
            variants = [memories[:i] + memories[i + 1:] for i in range(len(memories))]
            futures = [[executor.submit(trial, variant) for _ in range(RUNS_PER_VARIANT)]
                       for variant in variants]
            for memory, runs in zip(decision["retrieved"], futures):
                ablation = summarize([future.result() for future in runs])
                ablation["removed_memory_id"] = memory["memory_id"]
                ablation["flip_rate"] = sum(
                    action is not None and action != original_action
                    for action in ablation["actions"]
                ) / RUNS_PER_VARIANT
                doc["ablations"].append(ablation)

            doc["status"] = "no_clear_influence"
            if any(a["errors"] for a in doc["ablations"]):
                doc["status"] = "incomplete"
            elif doc["ablations"]:
                highest = max(a["flip_rate"] for a in doc["ablations"])
                leaders = [a for a in doc["ablations"] if a["flip_rate"] == highest]
                if highest >= THRESHOLD and len(leaders) == 1:
                    doc["culprit_memory_id"] = leaders[0]["removed_memory_id"]
                    doc["status"] = "influence_detected"

            # Optional escalation: fresh baseline and singles must be complete and
            # inconclusive before testing pairs. Never promote a pair to one culprit.
            if include_pairs and doc["status"] == "no_clear_influence":
                pairs = doc["pairs"]
                indices = list(combinations(range(len(memories)), 2))
                futures = [[executor.submit(trial, [m for k, m in enumerate(memories) if k not in pair])
                            for _ in range(RUNS_PER_VARIANT)] for pair in indices]
                for pair, runs in zip(indices, futures):
                    result = summarize([future.result() for future in runs])
                    result["removed_memory_ids"] = [decision["retrieved"][i]["memory_id"] for i in pair]
                    result["flip_rate"] = sum(a is not None and a != original_action for a in result["actions"]) / RUNS_PER_VARIANT
                    pairs["ablations"].append(result)
                pairs["status"] = "no_clear_influence"
                if any(a["errors"] for a in pairs["ablations"]):
                    pairs["status"] = "incomplete"
                else:
                    highest = max(a["flip_rate"] for a in pairs["ablations"])
                    leaders = [a for a in pairs["ablations"] if a["flip_rate"] == highest]
                    if highest >= THRESHOLD and len(leaders) == 1:
                        pairs["status"] = "group_influence_detected"
                        pairs["candidate_memory_ids"] = leaders[0]["removed_memory_ids"]

    doc["created_at"] = datetime.now(timezone.utc)
    doc["_id"] = db.replays().insert_one(doc).inserted_id
    return doc
