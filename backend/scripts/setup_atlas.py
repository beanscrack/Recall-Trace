"""Create collections, the memories validator, and both vector indexes; optionally wait and seed.

    python scripts/setup_atlas.py            # create + print status
    python scripts/setup_atlas.py --wait     # also wait until memory_vector_index is queryable
    python scripts/setup_atlas.py --seed     # wait, then seed demo data
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, seed  # noqa: E402

db.ensure_collections()
print("collections + validator: ok")
print("indexes:", db.ensure_indexes())
if "--wait" in sys.argv or "--seed" in sys.argv:
    print("waiting for memory_vector_index to be queryable ...")
    print("queryable:", db.wait_queryable())
if "--seed" in sys.argv:
    print("seeded:", seed.reset())
print("status:", db.index_status())
