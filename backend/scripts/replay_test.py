"""Offline replay checks with mocked LLM/collections; no Atlas or API keys used.

Run from backend/: .venv/bin/python scripts/replay_test.py
"""
import sys
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path
from threading import Barrier, Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId
from fastapi.testclient import TestClient

from app import main, replay, retrieval, sim
from app.errors import Conflict


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.ids = [ObjectId() for _ in range(3)]
        self.doc = {
            "_id": ObjectId(), "tenant_id": "acme-pay", "task": "recorded incident",
            "system_prompt": "recorded prompt", "action": "disable_fraud_checks",
            "model": {"provider": "recorded", "name": "old-model", "params": {"temperature": 0}},
            "tools": [{"name": name, "parameters": {}} for name in
                      ["disable_fraud_checks", "rollback_deployment", "escalate_incident"]],
            "retrieved": [{"memory_id": mid, "text": f"snapshot {i}", "version": 2, "score": .8}
                          for i, mid in enumerate(self.ids)],
        }
        self.original = deepcopy(self.doc)
        self.decisions = Mock()
        self.decisions.find_one.return_value = self.doc
        self.replays = Mock()
        self.replay_id = ObjectId()
        self.replays.insert_one.return_value = SimpleNamespace(inserted_id=self.replay_id)
        for target, value in [("decisions", self.decisions), ("replays", self.replays)]:
            p = patch.object(replay.db, target, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        # Fail immediately if replay accidentally retrieves or executes anything.
        for obj, name in [(replay.db, "memories"), (sim, "apply"), (sim, "reset"),
                          (sim, "get"), (retrieval, "search_memories")]:
            p = patch.object(obj, name, side_effect=AssertionError(f"Forbidden: {name}"))
            mock = p.start()
            self.addCleanup(p.stop)
            self.addCleanup(mock.assert_not_called)

    def run_replay(self, choose):
        with patch.object(replay.llm, "decide", side_effect=choose) as decide:
            result = replay.run_replay(str(self.doc["_id"]))
        self.decisions.find_one.assert_called_once_with({"_id": self.doc["_id"]})
        self.replays.insert_one.assert_called_once_with(result)
        self.assertEqual(result["_id"], self.replay_id)
        self.assertEqual(result["decision_id"], self.doc["_id"])
        self.assertEqual(result["tenant_id"], "acme-pay")
        self.assertIsNotNone(result["created_at"].tzinfo)
        self.assertEqual(self.doc, self.original)
        return result, decide

    def influenced(self, system, task, memories, tools, model):
        self.assertEqual((system, task, tools, model),
                         (self.doc["system_prompt"], self.doc["task"], self.doc["tools"], self.doc["model"]))
        action = "disable_fraud_checks" if any(m["memory_id"] == str(self.ids[0]) for m in memories) else "rollback_deployment"
        return {"action": action, "action_args": {}, "rationale": "mock"}

    def test_snapshot_order_inputs_and_influence(self):
        result, decide = self.run_replay(self.influenced)
        self.assertEqual(decide.call_count, 12)
        self.assertEqual(result["baseline"]["stability"], 1)
        self.assertTrue(result["stable"])
        self.assertEqual(result["original_action"], self.doc["action"])
        self.assertEqual([a["flip_rate"] for a in result["ablations"]], [1, 0, 0])
        self.assertEqual(result["culprit_memory_id"], self.ids[0])
        self.assertEqual(result["status"], "influence_detected")
        variants = Counter(tuple(m["memory_id"] for m in call.args[2]) for call in decide.call_args_list)
        ordered = tuple(map(str, self.ids))
        self.assertEqual(variants, Counter({ordered: 3, ordered[1:]: 3,
                                           (ordered[0], ordered[2]): 3, ordered[:2]: 3}))

    def test_unstable_baseline_stops(self):
        result, decide = self.run_replay(lambda *args: {"action": "rollback_deployment"})
        self.assertEqual(decide.call_count, 3)
        self.assertEqual(result["status"], "unstable_baseline")
        self.assertFalse(result["stable"])
        self.assertEqual(result["ablations"], [])
        self.assertIsNone(result["culprit_memory_id"])

    def test_baseline_and_flip_threshold_are_inclusive(self):
        counts = Counter()
        lock = Lock()
        def choose(system, task, memories, tools, model):
            key = tuple(m["memory_id"] for m in memories)
            with lock:
                counts[key] += 1
                run = counts[key]
            if len(memories) == 3:
                action = "disable_fraud_checks" if run <= 2 else "rollback_deployment"
            elif str(self.ids[0]) not in key and run <= 2:
                action = "rollback_deployment"
            else:
                action = "disable_fraud_checks"
            return {"action": action}

        result, _ = self.run_replay(choose)
        self.assertEqual(result["baseline"]["stability"], 2 / 3)
        self.assertTrue(result["stable"])
        self.assertEqual(result["ablations"][0]["flip_rate"], 2 / 3)
        self.assertEqual(result["culprit_memory_id"], self.ids[0])

    def test_no_flip(self):
        result, _ = self.run_replay(lambda *args: {"action": "disable_fraud_checks"})
        self.assertEqual(result["status"], "no_clear_influence")
        self.assertIsNone(result["culprit_memory_id"])

    def test_one_flip_in_three_is_below_threshold(self):
        counts = Counter()
        lock = Lock()
        def choose(s, t, memories, *args):
            key = tuple(m["memory_id"] for m in memories)
            with lock:
                counts[key] += 1
                run = counts[key]
            return {"action": "rollback_deployment" if len(memories) < 3 and run == 1
                    else "disable_fraud_checks"}
        result, _ = self.run_replay(choose)
        self.assertEqual([a["flip_rate"] for a in result["ablations"]], [1 / 3] * 3)
        self.assertEqual(result["status"], "no_clear_influence")
        self.assertIsNone(result["culprit_memory_id"])

    def test_tied_leaders_are_ambiguous(self):
        result, _ = self.run_replay(lambda s, t, m, *args: {
            "action": "disable_fraud_checks" if len(m) == 3 else "rollback_deployment"})
        self.assertEqual(result["status"], "no_clear_influence")
        self.assertIsNone(result["culprit_memory_id"])

    def test_baseline_failure_is_recorded_and_stops(self):
        def fail(*args):
            raise RuntimeError("secret provider response")
        result, decide = self.run_replay(fail)
        self.assertEqual(decide.call_count, 3)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["baseline"]["actions"], [None] * 3)
        self.assertFalse(result["stable"])
        self.assertEqual(len(result["baseline"]["errors"]), 3)
        self.assertNotIn("secret", str(result))
        self.assertEqual(result["ablations"], [])

    def test_ablation_failures_do_not_count_as_flips(self):
        def choose(s, t, m, *args):
            if len(m) < 3:
                raise TimeoutError()
            return {"action": "disable_fraud_checks"}
        result, _ = self.run_replay(choose)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["culprit_memory_id"])
        self.assertEqual([a["flip_rate"] for a in result["ablations"]], [0, 0, 0])

    def test_invalid_action_is_a_failed_request(self):
        result, _ = self.run_replay(lambda *args: {"action": "invented_tool"})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["baseline"]["errors"][0]["type"], "ValueError")

    def test_partial_failure_preserves_observed_actions_without_attribution(self):
        counts = Counter()
        lock = Lock()
        def choose(s, t, memories, *args):
            key = tuple(m["memory_id"] for m in memories)
            with lock:
                counts[key] += 1
                run = counts[key]
            if str(self.ids[0]) not in key:
                if run == 1:
                    raise TimeoutError()
                return {"action": "rollback_deployment"}
            return {"action": "disable_fraud_checks"}
        result, _ = self.run_replay(choose)
        ablation = result["ablations"][0]
        self.assertEqual(ablation["actions"].count(None), 1)
        self.assertEqual(ablation["flip_rate"], 2 / 3)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["culprit_memory_id"])

    def test_empty_memory_snapshot(self):
        self.doc["retrieved"] = []
        self.original = deepcopy(self.doc)
        result, decide = self.run_replay(lambda *args: {"action": "disable_fraud_checks"})
        self.assertEqual(decide.call_count, 3)
        self.assertEqual(result["ablations"], [])
        self.assertIsNone(result["culprit_memory_id"])

    def test_llm_calls_are_concurrent_and_inputs_are_isolated(self):
        barrier = Barrier(3, timeout=5)
        def choose(s, t, memories, tools, model):
            barrier.wait()
            self.assertEqual(model, self.original["model"])
            self.assertEqual(tools, self.original["tools"])
            model.clear()
            tools.clear()
            memories.clear()
            return {"action": "disable_fraud_checks"}
        result, _ = self.run_replay(choose)
        self.assertEqual(result["status"], "no_clear_influence")

    def test_missing_decision_never_calls_llm_or_inserts(self):
        self.decisions.find_one.return_value = None
        with patch.object(replay.llm, "decide") as decide:
            with self.assertRaisesRegex(Conflict, "Decision not found"):
                replay.run_replay(str(self.doc["_id"]))
        decide.assert_not_called()
        self.replays.insert_one.assert_not_called()

    def pair_run(self, choose):
        with patch.object(replay.llm, "decide", side_effect=choose) as calls:
            result = replay.run_replay(str(self.doc["_id"]), include_pairs=True)
        self.assertEqual(self.doc, self.original)
        self.assertEqual(result["tenant_id"], "acme-pay")
        self.replays.insert_one.assert_called_once_with(result)
        return result, calls

    def test_pair_redundant_memories_detected_without_single_culprit(self):
        def choose(system, task, memories, tools, model):
            self.assertEqual((system, task, tools, model), (self.doc["system_prompt"], self.doc["task"], self.doc["tools"], self.doc["model"]))
            ids = [m["memory_id"] for m in memories]
            self.assertEqual(ids, [str(i) for i in self.ids if str(i) in ids])
            return {"action": "disable_fraud_checks" if any(str(i) in ids for i in self.ids[:2]) else "rollback_deployment"}
        result, calls = self.pair_run(choose)
        self.assertEqual(calls.call_count, 21)
        self.assertEqual(result["status"], "no_clear_influence")
        self.assertIsNone(result["culprit_memory_id"])
        self.assertEqual(result["pairs"]["status"], "group_influence_detected")
        self.assertEqual(result["pairs"]["candidate_memory_ids"], self.ids[:2])
        self.assertEqual([a["flip_rate"] for a in result["pairs"]["ablations"]], [1, 0, 0])

    def test_pairs_skip_unstable_baseline(self):
        result, calls = self.pair_run(lambda *args: {"action": "rollback_deployment"})
        self.assertEqual(calls.call_count, 3)
        self.assertEqual(result["pairs"]["status"], "not_run")

    def test_pairs_skip_when_single_memory_detected(self):
        result, calls = self.pair_run(self.influenced)
        self.assertEqual(calls.call_count, 12)
        self.assertEqual(result["pairs"]["ablations"], [])

    def test_pair_ties_have_no_candidate(self):
        result, _ = self.pair_run(lambda s, t, m, *args: {"action": "rollback_deployment" if len(m) == 1 else "disable_fraud_checks"})
        self.assertEqual(result["pairs"]["status"], "no_clear_influence")
        self.assertEqual(result["pairs"]["candidate_memory_ids"], [])

    def test_pair_failure_is_not_a_flip(self):
        def choose(s, t, m, *args):
            if len(m) == 1:
                raise RuntimeError("private provider detail")
            return {"action": "disable_fraud_checks"}
        result, _ = self.pair_run(choose)
        self.assertEqual(result["pairs"]["status"], "incomplete")
        self.assertEqual(result["pairs"]["candidate_memory_ids"], [])
        self.assertTrue(all(a["flip_rate"] == 0 for a in result["pairs"]["ablations"]))
        self.assertNotIn("private provider detail", str(result))

    def test_single_failure_prevents_pairs(self):
        def choose(s, t, m, *args):
            if len(m) == 2:
                raise RuntimeError("failed")
            return {"action": "disable_fraud_checks"}
        result, calls = self.pair_run(choose)
        self.assertEqual(calls.call_count, 12)
        self.assertEqual(result["pairs"]["status"], "not_run")

    def test_four_memories_test_all_six_pairs(self):
        self.ids.append(ObjectId())
        self.doc["retrieved"].append({"memory_id": self.ids[-1], "text": "fourth", "version": 1})
        self.original = deepcopy(self.doc)
        result, calls = self.pair_run(lambda *args: {"action": "disable_fraud_checks"})
        self.assertEqual(calls.call_count, 33)
        self.assertEqual(len(result["pairs"]["ablations"]), 6)
        self.assertEqual(result["pairs"]["candidate_memory_ids"], [])

    def test_pair_threshold_inclusive(self):
        counts = Counter()
        lock = Lock()
        def choose(s, t, m, *args):
            key = tuple(x["memory_id"] for x in m)
            with lock:
                counts[key] += 1
                run = counts[key]
            return {"action": "rollback_deployment" if key == (str(self.ids[2]),) and run <= 2 else "disable_fraud_checks"}
        result, _ = self.pair_run(choose)
        self.assertEqual(result["pairs"]["status"], "group_influence_detected")
        self.assertEqual(result["pairs"]["ablations"][0]["flip_rate"], 2 / 3)

    def test_pair_size_guard_before_llm(self):
        self.doc["retrieved"] = self.doc["retrieved"][:1]
        with patch.object(replay.llm, "decide") as calls:
            with self.assertRaises(Conflict):
                replay.run_replay(str(self.doc["_id"]), include_pairs=True)
        calls.assert_not_called()

    def test_pair_route_serialization_and_isolation(self):
        with patch.object(replay.llm, "decide", return_value={"action": "disable_fraud_checks"}):
            response = TestClient(main.app).post(f"/api/decisions/{self.doc['_id']}/replay?include_pairs=true", headers={"X-User": "sre-oncall"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["pairs"]["ablations"]), 3)
        self.assertIsInstance(response.json()["pairs"]["ablations"][0]["removed_memory_ids"][0], str)
        self.decisions.find_one.return_value = None
        with patch.object(replay, "run_replay") as run:
            response = TestClient(main.app).post(f"/api/decisions/{self.doc['_id']}/replay?include_pairs=true", headers={"X-User": "platform-lee"})
        self.assertEqual(response.status_code, 404)
        run.assert_not_called()

    def test_existing_route_serializes_replay(self):
        with patch.object(replay.llm, "decide", side_effect=self.influenced):
            response = TestClient(main.app).post(
                f"/api/decisions/{self.doc['_id']}/replay", headers={"X-User": "sre-oncall"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["_id"], str(self.replay_id))
        self.assertEqual(result["culprit_memory_id"], str(self.ids[0]))
        self.assertEqual(self.decisions.find_one.call_args_list[0].args[0],
                         {"_id": self.doc["_id"], "tenant_id": "acme-pay"})

    def test_route_refuses_other_tenant_before_replay(self):
        self.decisions.find_one.return_value = None
        with patch.object(replay, "run_replay") as run:
            response = TestClient(main.app).post(
                f"/api/decisions/{self.doc['_id']}/replay", headers={"X-User": "platform-lee"})
        self.assertEqual(response.status_code, 404)
        run.assert_not_called()
        self.decisions.find_one.assert_called_once_with(
            {"_id": self.doc["_id"], "tenant_id": "globex"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
