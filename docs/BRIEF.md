# RecallTrace: build brief

This brief is for a Claude Code session that will create the repo and build the project with a team of three. Read it fully before scaffolding. Where it gives a default, use it unless a teammate says otherwise. Where it marks something as an open decision, ask before guessing.

## 1. Context

- **Event:** MongoDB hackathon, Track 2, "Memory You Can Govern". The agent must persist and retrieve memory with MongoDB Atlas and Vector Search, memory must change what it does on the next run, and there must be rules for who can read each memory, how long it lives, and how it gets corrected or forgotten.
- **Constraints:** 5 hours of build time, 3 people, data lives in the hackathon's Atlas sandbox.
- **Judging:** a 3-minute live demo plus 1 to 2 minutes of questions. Technical demo 35%, implementation difficulty 30%, impact 20%, creativity 15%. The demo working live matters more than anything else in this document.

**One-line pitch:** RecallTrace traces evidence of memory influence on an agent's decision, proposes a correction against verified evidence with human sign-off, and measures behavior on the next run.

**The three track questions, and our answers:**

| Track question | Our answer |
|---|---|
| How do you keep one team's memory from leaking into another's? | Every agent read goes through one retrieval function that applies a tenant filter inside `$vectorSearch`. The tenant comes from the session, never from the model. |
| How does the agent fix or drop a memory that is wrong or expired? | Wrong: the court quarantines it and writes a corrected version that supersedes it, after a human approves. Expired: an `expires_at` filter at retrieval. Nothing is deleted, so history stays auditable. |
| How do you prove a memory changed behavior and didn't just fill the prompt? | Counterfactual replay (Black Box): rerun the exact recorded decision step with each retrieved memory removed and measure how often the chosen action flips. |

## 2. The demo that must work

This is the definition of done. Build toward this path and nothing else until it works end to end.

1. An incident-response agent for tenant `acme-pay` gets a checkout incident. It retrieves memories from Atlas, including a stale one, and calls `disable_fraud_checks` on a simulated checkout system. The simulation's fraud rate goes red.
2. A reviewer clicks **Contest decision**. Black Box replays the recorded step with each retrieved memory removed and shows a flip rate per memory. The stale memory is the clear culprit.
3. RecallTrace looks up newer verified evidence for the same tenant, proposes quarantining the stale memory and replacing it with a corrected version, and shows the reason.
4. The reviewer clicks **Approve**. The old memory is quarantined, the new version is stored with a link to the old one and to the evidence, and the approval is recorded with the reviewer's name.
5. The simulation is reset and the same task is run again through real retrieval. The agent now calls `rollback_deployment`. The dashboard shows before and after side by side.
6. Switch the session to tenant `globex`. Run a query that would match Acme's memories. Nothing from Acme comes back, and a direct request for an Acme memory ID is refused and logged.

## 3. Scope

**In:**
- One agent, one decision step, three tools.
- A simulated checkout system held in a single Mongo document or in process memory.
- Single-step replay that removes one memory at a time.
- Human-approved correction.
- Two tenants and one expired memory.

**Out, do not build:**
- Real authentication. A session picker in the UI maps a user to a tenant on the backend.
- Multi-step agent loops, streaming, websockets, Docker, CI.
- Automatic detection of bad decisions. A human contests the decision, prompted by the simulation's red fraud rate.
- Removing combinations of memories in replay.
- Test suites beyond the two scripts in section 9.

## 4. Defaults

| Area | Default | Notes |
|---|---|---|
| Backend | Python 3.11+, FastAPI, `pymongo` | Async route handlers are fine; keep Mongo calls simple. |
| Frontend | React, Vite, TypeScript, Tailwind | One page. Plain `fetch`, no state library. |
| Embeddings | Voyage AI `voyage-4`, 1024 dimensions | Set through `EMBEDDING_MODEL`. The index dimension must match. |
| LLM | Open decision | Read provider and model from `LLM_PROVIDER` and `LLM_MODEL`. Must support tool calling with a forced tool choice. |
| Database | `memory_court` | Do not create or modify anything outside this database. |

Environment variables, in `.env.example` with no real values:

```
MONGODB_URI=
MONGODB_DB=memory_court
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
EMBEDDING_MODEL=voyage-4
EMBEDDING_DIM=1024
VOYAGE_API_KEY=
```

Never commit `.env` or print keys. Add `.env` to `.gitignore` in the first commit.

The MongoDB MCP server (`npx mongodb-mcp-server@latest setup`, connection string in `MDB_MCP_CONNECTION_STRING`) is for inspecting data from this session while building. The application itself talks to Atlas through `pymongo`.

## 5. Repo layout

```
recalltrace/
  README.md
  .env.example
  .gitignore
  backend/
    requirements.txt
    app/
      main.py          FastAPI routes
      config.py        env loading
      db.py            client, collection handles, index and validator setup
      embeddings.py    embed(texts) -> vectors
      llm.py           decide() and propose_correction(), provider hidden behind them
      retrieval.py     the only code path that reads memories for the agent
      agent.py         run_task: retrieve -> decide -> record -> act on the simulation
      replay.py        Black Box
      court.py         verdict proposal and approval
      sim.py           simulated checkout system
      seed.py          reset and reseed everything
    scripts/
      flip_test.py
      isolation_check.py
  frontend/
```

## 6. Data model

This is the contract between the three workstreams. Agree on it before writing code, and change it only by telling the other two people.

### `memories`

```json
{
  "_id": "ObjectId",
  "tenant_id": "acme-pay",
  "service": "checkout",
  "text": "INC-212: checkout 5xx spike with fraud-check p99 over 4s ...",
  "embedding": [0.01, "... 1024 floats"],
  "status": "active",
  "version": 1,
  "supersedes": null,
  "superseded_by": null,
  "source": "agent_learned",
  "source_evidence_id": null,
  "created_by": "agent:incident-responder",
  "created_at": "2026-02-10T00:00:00Z",
  "expires_at": "2099-01-01T00:00:00Z"
}
```

- `service` explicitly identifies the incident domain; seeds and corrected versions preserve it. Corrective evidence must have the same tenant and service, a newer date, and a nonblank verifier. Untagged legacy memories receive no automatic corrective evidence.
- `status` is `active` or `quarantined`.
- `expires_at` is always a date. Use a far-future date for memories that do not expire, so the retrieval filter is a plain range comparison.
- Corrections never edit `text` in place. They insert a new document with `version + 1` and `supersedes` set, then mark the old one `quarantined` with `superseded_by` set.

### `evidence`

Verified records the court checks against. The agent's retrieval never reads this collection.

```json
{
  "_id": "ObjectId",
  "tenant_id": "acme-pay",
  "service": "checkout",
  "title": "Postmortem PM-31",
  "text": "Disabling fraud checks during INC-212-style incidents caused ...",
  "embedding": ["... 1024 floats"],
  "verified_by": "risk-lead@acme-pay",
  "created_at": "2026-09-18T00:00:00Z"
}
```

### `decisions`

The replay record. It must contain everything needed to rerun the step without touching the database again.

```json
{
  "_id": "ObjectId",
  "tenant_id": "acme-pay",
  "user_id": "sre-oncall",
  "task": "Checkout API 5xx rate is 18% ...",
  "system_prompt": "full text",
  "model": {"provider": "...", "name": "...", "params": {}},
  "tools": ["full tool definitions as sent"],
  "retrieved": [
    {"memory_id": "ObjectId", "version": 1, "score": 0.83, "text": "snapshot of the text as retrieved"}
  ],
  "action": "disable_fraud_checks",
  "action_args": {},
  "rationale": "model's short stated reason",
  "sim_before": {},
  "sim_after": {},
  "contested": null,
  "rerun_of": null,
  "created_at": "..."
}
```

### `replays`

```json
{
  "_id": "ObjectId",
  "decision_id": "ObjectId",
  "runs_per_variant": 3,
  "baseline": {"actions": ["disable_fraud_checks", "disable_fraud_checks", "disable_fraud_checks"], "stability": 1.0},
  "ablations": [
    {"removed_memory_id": "ObjectId", "actions": ["rollback_deployment", "rollback_deployment", "rollback_deployment"], "flip_rate": 1.0}
  ],
  "culprit_memory_id": "ObjectId",
  "created_at": "..."
}
```

### `verdicts`

```json
{
  "_id": "ObjectId",
  "decision_id": "ObjectId",
  "replay_id": "ObjectId",
  "memory_id": "ObjectId",
  "evidence_id": "ObjectId",
  "outcome": "correct",
  "reason": "short explanation",
  "proposed_text": "corrected memory text",
  "status": "proposed",
  "approved_by": null,
  "approved_at": null,
  "new_memory_id": null
}
```

- `outcome` is `correct`, `quarantine`, or `no_action`.
- `status` is `proposed`, `approved`, or `rejected`.

### `access_log`

One document per memory read or refused read: `tenant_id`, `user_id`, `kind` (`search` or `get`), `query`, `returned_ids`, `allowed`, `at`.

## 7. Atlas setup

### Vector index on `memories`

Name it `memory_vector_index`. Create it in the first half hour, because the index builds asynchronously and is not queryable right away.

```python
from pymongo.operations import SearchIndexModel

db.memories.create_search_index(model=SearchIndexModel(
    name="memory_vector_index",
    type="vectorSearch",
    definition={"fields": [
        {"type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine"},
        {"type": "filter", "path": "tenant_id"},
        {"type": "filter", "path": "status"},
        {"type": "filter", "path": "expires_at"},
    ]},
))
```

Poll `db.memories.list_search_indexes()` until the index reports `queryable: true` before seeding assertions or running retrieval.

### Vector index on `evidence`

Same shape, named `evidence_vector_index`, with a filter on `tenant_id`. If the sandbox limits the number of search indexes, skip this one and match evidence on a `service` tag field with a normal query.

### Retrieval query

`retrieval.search_memories(tenant_id, user_id, query, k=4)` is the only function the agent uses to read memories. It takes `tenant_id` from the session object passed in by the route handler. The model never supplies or sees a tenant parameter.

```python
pipeline = [
    {"$vectorSearch": {
        "index": "memory_vector_index",
        "path": "embedding",
        "queryVector": query_vector,
        "numCandidates": 100,
        "limit": k,
        "filter": {"$and": [
            {"tenant_id": {"$eq": tenant_id}},
            {"status": {"$eq": "active"}},
            {"expires_at": {"$gt": now}},
        ]},
    }},
    {"$set": {"score": {"$meta": "vectorSearchScore"}}},
    {"$unset": "embedding"},
]
```

Every call writes an `access_log` entry.

### Schema validation (10 minutes, do it if time allows)

Add a JSON schema validator on `memories` that requires `tenant_id`, `text`, `status` (enum), `version`, `created_at`, and `expires_at`. It means a memory without a tenant cannot be written at all, which is a good answer in Q&A.

## 8. Core logic

### Simulated checkout (`sim.py`)

State: `fraud_checks_enabled`, `deployment_version`, `checkout_error_rate`, `fraud_rate`, `incident_status`.

| Tool | Effect on the simulation |
|---|---|
| `disable_fraud_checks` | Error rate drops to normal. Fraud rate jumps to a red value. |
| `rollback_deployment` | Deployment version goes back one. Error rate drops to normal. Fraud rate unchanged. |
| `escalate_incident` | Nothing changes except `incident_status` becomes `escalated`. |

Provide `reset()` that restores the incident state.

### The decision function (`llm.py`)

```
decide(system_prompt, task, memories, tools, model) -> {action, action_args, rationale}
```

- A pure function of its arguments. It does no retrieval and no database access. The live run and the replay both call it, which is what makes the replay a fair comparison.
- Force a tool call so the output is always exactly one of the three actions.
- Memories are rendered into the prompt in the order given, each with its ID, so the layout is identical between runs.
- Use temperature 0 if the model accepts the parameter. If it does not, rely on the forced tool choice and repeated runs.

### Live run (`agent.py`)

`run_task(session, task)`: call `search_memories`, call `decide`, apply the action to the simulation, write the `decisions` document with full snapshots, return it.

### Black Box replay (`replay.py`)

Input: a decision ID. Everything comes from the stored `decisions` document. Do not re-query memories.

1. **Baseline:** call `decide` N times (N = 3) with all recorded memories. `stability` is the share of runs that match the original action. If stability is below 2/3, report that the decision is unstable and stop, because flip rates would be meaningless.
2. **Ablations:** for each recorded memory, call `decide` N times with that memory removed. `flip_rate` is the share of runs whose action differs from the original.
3. **Candidate influential memory:** the unique memory with the highest flip rate, if that rate is at least 2/3. A tie or a failed LLM request leaves `culprit_memory_id` unset. Replay measures evidence of influence, not proof of causation.
4. Run the calls concurrently. With 4 memories and N = 3 this is 15 calls and should finish in a few seconds.
5. Store the `replays` document and return it.

Results retain `stable` and `original_action` for teammate compatibility and add `tenant_id`, `status`, and per-variant `errors`. Status is `influence_detected`, `no_clear_influence`, `unstable_baseline`, or `incomplete`. Failed trials occupy `null` action slots and do not count as flips; rates use all scheduled runs as the denominator. A baseline failure stops ablations. Incomplete comparisons never nominate a memory.

The replay never touches the simulation.

### Evidence review (`court.py`)

`propose_verdict(decision_id)`:

1. Take the culprit memory from the replay.
2. Find candidate evidence: same tenant and explicit `service`, `created_at` newer than the memory, and a nonblank `verified_by`, closest by vector search. If the index is absent/building, use a normal query with the same eligibility predicates; untagged memories have no corrective evidence. The rule "verified, newer, and about the same thing" is a lookup, not a model judgment.
3. If no evidence is found, propose `quarantine` with the replay result as the reason.
4. If evidence is found, make one LLM call that receives the memory text and the evidence text and returns structured output: `contradicts` (boolean), `reason`, `corrected_text`. If `contradicts` is false, propose `no_action`.
5. Store the verdict as `proposed`.

`approve_verdict(verdict_id, approved_by)`:

1. Set the old memory to `quarantined`.
2. For `correct`, insert the new memory: `version + 1`, `supersedes` the old ID, `source: "court_correction"`, `source_evidence_id`, a fresh embedding of `proposed_text`. Set `superseded_by` on the old one.
3. Mark the verdict `approved` with `approved_by`, `approved_at`, and `new_memory_id`.

The model only drafts. Nothing changes in `memories` until a human approves.

## 9. Build order

### Gate 0: the flip test (first 30 minutes, before any other feature)

`scripts/flip_test.py` uses no database. It hardcodes the task and the seed memory texts, calls `decide` 5 times with the stale memory present and 5 times without it, and prints the actions.

**Pass:** with the stale memory, `disable_fraud_checks` at least 4 of 5 times. Without it, any other action at least 4 of 5 times.

If it fails, tune the stale memory wording, the task wording, and the system prompt until it passes. Models tend to be cautious about disabling a safety control, so the stale memory needs to read like an approved runbook step with a concrete past success. Do not move on until this passes; the whole demo depends on it. Copy the final wording into `seed.py`.

### Then

1. Scaffold the repo, `.env.example`, `db.py`, and create both vector indexes.
2. `seed.py` and `POST /api/demo/reset`.
3. `retrieval.py`, `sim.py`, `agent.py`, and `POST /api/run`. Frontend builds against mock JSON matching section 6 in parallel.
4. **Checkpoint at hour 2:** run the task from the dashboard and see the decision and the red fraud rate. If this is not working, stop adding features and fix it.
5. `replay.py` and its panel.
6. `court.py`, approval, and its panel.
7. Rerun with before and after view.
8. Tenant switcher, `isolation_check.py`, and the refused direct read.
9. **Feature freeze at 3:30.** Then rehearsal, a recorded backup video, and nothing new.

`scripts/isolation_check.py` runs several queries as `globex` that are semantically close to Acme memories and asserts that no returned document has `tenant_id` other than `globex`, and the same in reverse.

## 10. API

All routes read the session user from an `X-User` header. The backend maps user to tenant from a hardcoded table. No route accepts a tenant ID from the client.

| Route | Purpose |
|---|---|
| `POST /api/run` | Body `{task}`. Runs the agent, returns the decision. Optional `rerun_of`. |
| `GET /api/decisions/{id}` | Decision with its replay and verdict if they exist. |
| `POST /api/decisions/{id}/contest` | Body `{reason}`. Marks the decision contested by the session user. |
| `POST /api/decisions/{id}/replay` | Runs Black Box, returns the replay. |
| `POST /api/decisions/{id}/verdict` | Proposes a verdict. |
| `POST /api/verdicts/{id}/approve` | Approves as the session user. |
| `GET /api/memories` | The session tenant's memories, including quarantined ones and version links. |
| `GET /api/memories/{id}` | Returns 404 and writes a refused `access_log` entry if the memory belongs to another tenant. |
| `GET /api/access-log` | Recent entries for the session tenant. |
| `GET /api/sim` / `POST /api/sim/reset` | Simulation state. |
| `POST /api/demo/reset` | Drops and reseeds all collections, resets the simulation. |

## 11. Seed data

All names, incidents, and figures here are invented for the demo.

**Users:** `sre-oncall` and `reviewer-dana` belong to `acme-pay`. `platform-lee` belongs to `globex`.

**Task:**
> Checkout API 5xx rate is 18% and rising. Fraud-check service p99 latency is 4.2s. Deploy v2.4.1 went out 10 minutes ago. Choose one action.

**Acme memories:**

| # | Text | Notes |
|---|---|---|
| 1 | INC-212: checkout 5xx spike with fraud-check p99 over 4s. Rollback did not help. Disabling fraud checks restored checkout in 4 minutes. Runbook step: when this pattern appears, disable fraud checks first. | **The stale memory.** Created February 2026, `agent_learned`. Final wording comes from the flip test. |
| 2 | Rolling back checkout-api takes about 6 minutes and needs no approval for versions deployed in the last 24 hours. | Distractor, relevant. |
| 3 | Escalate to the payments on-call lead when the error rate stays above 25% for 15 minutes. | Distractor, relevant. |
| 4 | Fraud-check service is owned by the Risk team, reachable in #risk-oncall. | Distractor. |
| 5 | INC-240: payment gateway timeouts were caused by an expired TLS certificate; fixed by rotating it. | Distractor. |
| 6 | INC-198: cart service memory leak, fixed by restarting the pods. | Distractor. |
| 7 | Temporary: deploy freeze on checkout-api, do not roll back or deploy. | **Expired.** `expires_at` in June 2026. Must never be retrieved. |

**Acme evidence:**

> Postmortem PM-31 (September 2026). Disabling fraud checks during the INC-212 pattern led to $184k in chargebacks. Policy: fraud checks must never be disabled as a mitigation. Fraud-check latency in these incidents is a symptom of the connection-pool regression in v2.x deploys. For checkout 5xx after a deploy, roll back the deployment.

**Globex memories:**

| # | Text | Notes |
|---|---|---|
| 8 | Globex INC-77: checkout 5xx with slow fraud checks was fixed by scaling the fraud-check pool to 12 replicas. | Semantically the closest match to the Acme task, which makes the isolation check convincing. |
| 9 | Globex checkout failover to the backup processor takes 90 seconds and is triggered from the ops console. | Private to Globex. |

Memory 7 also guards the demo: if the expiry filter breaks, the agent may refuse to roll back.

## 12. Frontend

One page, top to bottom, matching the order of the demo:

1. **Header:** session user picker (which switches tenant), **Reset demo** button.
2. **Incident:** the task text, simulation gauges for error rate and fraud rate, **Run agent** button.
3. **Decision:** the action chosen, the model's rationale, the retrieved memories with scores. **Contest decision** button.
4. **Investigation (Black Box):** one row per retrieved memory showing the actions when it was removed and the flip rate. Baseline row on top. Culprit highlighted.
5. **Verdict (RecallTrace):** stale memory text beside proposed text, the evidence title and excerpt, the reason, **Approve** button, and after approval, who approved and when.
6. **Rerun:** before and after cards side by side: action, memories used, simulation outcome.
7. **Isolation:** visible when signed in as Globex: the search result list and the refused read from the access log.

Build against static JSON shaped like section 6 until the backend routes exist. Readable from the back of a room matters more than visual polish: large type for actions and flip rates.

## 13. Demo script (3 minutes)

| Time | What happens | What to say |
|---|---|---|
| 0:00 | Dashboard open on the incident | One line: agents act on memories, and a wrong memory repeats the same mistake forever. |
| 0:20 | Run agent. It disables fraud checks. Fraud rate goes red. | The agent followed something it remembered. Which memory influenced that choice? |
| 0:50 | Contest, run Black Box. Flip-rate table fills in. | We replay the exact step with each memory removed. Remove this one and the decision changes every time. |
| 1:30 | Verdict appears. Approve. | The court checks newer verified evidence, proposes a correction, and a named human approves. The old version is kept and linked. |
| 2:05 | Reset simulation, rerun. Agent rolls back. Before and after shown. | Same task, same retrieval path, different memory, safe action. |
| 2:35 | Switch to Globex. Search returns no Acme memories. Refused read in the log. | Tenant filtering happens inside the vector search, and the tenant comes from the session. |
| 2:55 | Close | One line on who needs this. |

## 14. Likely questions

- **Is the tenant filter just application code?** Yes, in one function that the agent cannot bypass, with the filter applied inside `$vectorSearch` so other tenants' vectors are never candidates. Per-tenant database users would be the production step.
- **What if two memories cause the failure together?** Leave-one-out replay would show partial flip rates for both. Testing pairs is the next step and is out of scope here.
- **How do you know the flip isn't noise?** Each variant runs several times, and the baseline's stability is measured first.
- **Why is a human in the loop?** A system that rewrites its own memory unsupervised creates the governance problem the track is about. The court drafts, a person signs.
- **Why not delete bad or expired memories?** Deleting them destroys the record of why the agent acted. Quarantine and expiry filters keep them out of retrieval while keeping the history.

## 15. Open decisions to confirm with the team

1. LLM provider and model, and whether the hackathon supplies keys.
2. How many search indexes the sandbox allows.
3. Whether the app must run inside the sandbox environment or only the data must live there.
4. The one-line target user for the impact score.

## 16. How to work in this session

- Start with the scaffold and Gate 0. Report the flip test output before building further.
- Keep files small and the dependency list short. Prefer the obvious implementation.
- Three people are working in this repo. Commit small, and do not reformat or restructure files you were not asked to change.
- If something in this brief conflicts with what the sandbox allows, say so and propose the smallest change rather than working around it silently.
