"""Offline regression: a failed LLM decision must not execute a tool or save a decision."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId
from app import agent, sim


class AgentFailureTest(unittest.TestCase):
    def test_provider_failure_changes_neither_simulator_nor_decision_history(self):
        memories = [{'_id': ObjectId(), 'version': 1, 'score': .9, 'text': 'recorded memory'}]
        before = sim.get()
        with patch.object(agent, 'search_memories', return_value=memories), \
             patch.object(agent, 'decide', side_effect=RuntimeError('provider unavailable')), \
             patch.object(agent.db, 'decisions') as decisions, \
             patch.object(sim, 'apply') as apply:
            with self.assertRaisesRegex(RuntimeError, 'provider unavailable'):
                agent.run_task({'tenant_id': 'acme-pay', 'user_id': 'sre-oncall'}, 'incident')
            apply.assert_not_called()
            decisions.assert_not_called()
        self.assertEqual(sim.get(), before)

    def test_retrieval_failure_never_calls_llm_or_executes_tool(self):
        with patch.object(agent, 'search_memories', side_effect=RuntimeError('retrieval unavailable')), \
             patch.object(agent, 'decide') as decide, \
             patch.object(agent.db, 'decisions') as decisions, \
             patch.object(sim, 'apply') as apply:
            with self.assertRaisesRegex(RuntimeError, 'retrieval unavailable'):
                agent.run_task({'tenant_id': 'acme-pay', 'user_id': 'sre-oncall'}, 'incident')
            decide.assert_not_called()
            apply.assert_not_called()
            decisions.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
