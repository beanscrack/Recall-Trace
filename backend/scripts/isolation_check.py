"""Run cross-tenant-ish queries as each tenant and assert nothing from the other tenant comes back.
Requires seeded data.  Run from backend/:  python scripts/isolation_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.retrieval import get_memory, search_memories  # noqa: E402
from app.seed import TASK  # noqa: E402

CASES = {
    ("globex", "platform-lee"): [TASK, "disable fraud checks runbook INC-212",
                                 "how long does a checkout-api rollback take", "Risk team fraud-check owner"],
    ("acme-pay", "sre-oncall"): ["scale the fraud-check pool to 12 replicas",
                                 "failover to the backup processor from the ops console"],
}

failures = 0
for (tenant, user), queries in CASES.items():
    for q in queries:
        docs = search_memories(tenant, user, q)
        leaked = [d for d in docs if d["tenant_id"] != tenant]
        failures += bool(leaked)
        print(f"{'LEAK' if leaked else 'ok  '} {tenant:<9} {len(docs)} results  {q[:60]}")
    other = db.memories().find_one({"tenant_id": {"$ne": tenant}}, {"_id": 1})
    refused = get_memory(tenant, user, str(other["_id"])) is None
    failures += not refused
    print(f"{'ok  ' if refused else 'LEAK'} {tenant:<9} direct read of other tenant's memory refused={refused}")

print("PASS" if failures == 0 else f"FAIL ({failures})")
sys.exit(1 if failures else 0)
