"""Reset and reseed everything. All names, incidents, and figures are invented.

The text constants here are the single source of truth; scripts/flip_test.py imports them
without touching the database. Tune STALE_MEMORY / TASK there until Gate 0 passes.
"""
from datetime import datetime, timezone

from . import db, sim
from .embeddings import embed

TASK = ("Checkout API 5xx rate is 18% and rising. Fraud-check service p99 latency is 4.2s. "
        "Deploy v2.4.1 went out 10 minutes ago. Choose one action.")

STALE_MEMORY = ("INC-212: checkout 5xx spike with fraud-check p99 over 4s. Rollback did not help. "
                "Disabling fraud checks restored checkout in 4 minutes. Runbook step: when this "
                "pattern appears, disable fraud checks first.")

NEVER = datetime(2099, 1, 1, tzinfo=timezone.utc)


def _d(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


# (key, tenant, text, created_at, expires_at, source)
MEMORIES = [
    ("stale", "acme-pay", STALE_MEMORY, _d(2026, 2, 10), NEVER, "agent_learned"),
    ("rollback", "acme-pay", "Rolling back checkout-api takes about 6 minutes and needs no approval for "
     "versions deployed in the last 24 hours.", _d(2026, 3, 2), NEVER, "agent_learned"),
    ("escalate", "acme-pay", "Escalate to the payments on-call lead when the error rate stays above 25% "
     "for 15 minutes.", _d(2026, 3, 15), NEVER, "human"),
    ("owner", "acme-pay", "Fraud-check service is owned by the Risk team, reachable in #risk-oncall.",
     _d(2026, 1, 20), NEVER, "human"),
    ("tls", "acme-pay", "INC-240: payment gateway timeouts were caused by an expired TLS certificate; "
     "fixed by rotating it.", _d(2026, 4, 8), NEVER, "agent_learned"),
    ("leak", "acme-pay", "INC-198: cart service memory leak, fixed by restarting the pods.",
     _d(2026, 1, 5), NEVER, "agent_learned"),
    ("freeze", "acme-pay", "Temporary: deploy freeze on checkout-api, do not roll back or deploy.",
     _d(2026, 6, 1), _d(2026, 6, 30), "human"),
    ("globex_pool", "globex", "Globex INC-77: checkout 5xx with slow fraud checks was fixed by scaling the "
     "fraud-check pool to 12 replicas.", _d(2026, 5, 1), NEVER, "agent_learned"),
    ("globex_failover", "globex", "Globex checkout failover to the backup processor takes 90 seconds and is "
     "triggered from the ops console.", _d(2026, 5, 3), NEVER, "human"),
]

EVIDENCE = [
    ("acme-pay", "Postmortem PM-31",
     "Postmortem PM-31 (September 2026). Disabling fraud checks during the INC-212 pattern led to $184k in "
     "chargebacks. Policy: fraud checks must never be disabled as a mitigation. Fraud-check latency in these "
     "incidents is a symptom of the connection-pool regression in v2.x deploys. For checkout 5xx after a "
     "deploy, roll back the deployment.",
     "risk-lead@acme-pay", _d(2026, 9, 18), "checkout"),
]

# Explicit domain metadata for the canonical demo seeds. Kept separate from the
# existing tuple contract so flip-test and teammate seed consumers stay compatible.
SERVICE_BY_SEED = {
    "stale": "checkout", "rollback": "checkout", "escalate": "checkout",
    "owner": "checkout", "freeze": "checkout", "globex_pool": "checkout",
    "globex_failover": "checkout", "tls": "payment-gateway", "leak": "cart",
}


def reset() -> dict:
    """Clears documents (delete_many, not drop: dropping would also drop the search indexes)."""
    # Generate before deleting: a Voyage outage must not erase the current demo.
    vecs = embed([m[2] for m in MEMORIES] + [e[2] for e in EVIDENCE])
    db.ensure_collections()
    d = db.get_db()
    for name in db.COLLECTIONS:
        d[name].delete_many({})

    mem_docs = [{
        "tenant_id": tenant, "text": text, "embedding": vecs[i], "status": "active", "version": 1,
        "service": SERVICE_BY_SEED[key],
        "supersedes": None, "superseded_by": None, "source": source, "source_evidence_id": None,
        "created_by": "agent:incident-responder" if source == "agent_learned" else "human:seed",
        "created_at": created, "expires_at": expires, "seed_key": key,
    } for i, (key, tenant, text, created, expires, source) in enumerate(MEMORIES)]
    db.memories().insert_many(mem_docs)

    ev_docs = [{
        "tenant_id": tenant, "title": title, "text": text, "embedding": vecs[len(MEMORIES) + i],
        "verified_by": by, "created_at": created, "service": service,
    } for i, (tenant, title, text, by, created, service) in enumerate(EVIDENCE)]
    db.evidence().insert_many(ev_docs)

    sim.reset()
    return {"memories": len(mem_docs), "evidence": len(ev_docs)}
