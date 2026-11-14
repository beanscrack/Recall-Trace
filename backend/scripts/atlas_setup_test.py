"""Offline checks: index readiness gates demo seeding. Run from backend/."""
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, seed


class AtlasSetupTest(unittest.TestCase):
    def check_setup(self, ready):
        script = Path(__file__).with_name("setup_atlas.py")
        with patch.object(sys, "argv", [str(script), "--seed"]), \
             patch.object(db, "ensure_collections"), \
             patch.object(db, "ensure_indexes", return_value={}), \
             patch.object(db, "index_status", return_value={}), \
             patch.object(db, "wait_queryable", return_value=ready), \
             patch.object(seed, "reset") as reset:
            if ready:
                runpy.run_path(str(script), run_name="__main__")
                reset.assert_called_once_with()
            else:
                with self.assertRaisesRegex(SystemExit, "no demo data was replaced"):
                    runpy.run_path(str(script), run_name="__main__")
                reset.assert_not_called()

    def test_timeout_prevents_seed(self):
        self.check_setup(False)

    def test_ready_index_allows_seed(self):
        self.check_setup(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
