# Hackathon resource guide alignment

Reviewed against the supplied **Agents in Context Toronto: A MongoDB Hackathon Resource Guide**, November 14, 2026, pages 2–7. This is an implementation review, not evidence that live services have passed. The initial review had no service credentials; see the follow-up validation below for subsequent live Atlas and Voyage results.

## Required track capabilities

RecallTrace targets statement two, **Memory You Can Govern** (page 2).

| Requirement | Implementation | Verification / remaining gap |
| --- | --- | --- |
| Event-issued Atlas Sandbox (page 3) | `MONGODB_URI` connects PyMongo to Atlas | Must confirm the cluster was created through the event invitation; a hostname alone cannot establish eligibility |
| Persist and retrieve memory with Vector Search | `embeddings.py`, `retrieval.py`, `db.py` | Query uses `$vectorSearch`; live sandbox and index-readiness checks remain |
| Memory affects the next run | `agent.py` records retrieval; `court.py` quarantines and inserts a newly embedded version | Pass the real LLM flip gate and corrected rerun; the mock UI is not proof |
| Tenant separation | Session-derived tenant filter inside Vector Search; direct-read refusal and access log | Run `scripts/isolation_check.py` and verify refused direct reads |
| Expiry and correction | `expires_at` and active-status retrieval filters; versioned correction after approval | Verify expired seed memory is absent and correction links are intact in Atlas |
| Explain behavioral influence | Recorded prompt/model/tools/text snapshots; repeated leave-one-out replay | Offline tests pass; measure real-provider variability during rehearsal |
| Public repository and accessible demo (page 3) | Repository is public | Dashboard is currently a mock prototype; deploy/wire a working demo and verify access |

## Why Atlas is essential

Atlas is the source of retrievable memory and the persistent record of decisions, replay measurements, evidence, verdicts, and access events. Correcting a memory changes its retrieval eligibility and introduces a new embedded version for the next run. Replay reads stored decision snapshots instead of querying current memories, preserving an auditable comparison.

The current query correctly uses tenant, status, and date pre-filters, all indexed as filter fields. MongoDB documents these supported [Vector Search filters](https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage/). Voyage calls distinguish query embeddings from document embeddings, as recommended in the [official text embedding documentation](https://www.mongodb.com/docs/voyageai/models/text-embeddings/). Index dimensions must remain equal to `EMBEDDING_DIM` (1024 by default).

The simulator is process-local, with state snapshots stored in Atlas decisions. It does not provide durable simulation state or multi-worker consistency. Run one backend worker for this demo; do not describe it as a durable workflow engine.

## Guide technologies: required versus optional

| Resource in the guide | Relevance and decision |
| --- | --- |
| Atlas Sandbox + Vector Search | Required and central to the chosen track |
| Voyage embeddings | Already used for memory, evidence, and query vectors |
| Schema validation | Memory validator requires tenant, status, version, and timestamps; setup must be run against Atlas |
| MongoDB MCP server | Repository config exists and defaults to read-only; live connection remains unverified |
| MongoDB Agent Skills / query-prompting guide | Recommended developer aids; installation/use has not been verified |
| Atlas Managed MCP / marketplace connectors | Alternative development connectivity; not needed in addition to the configured local MCP server |
| Atlas Search, automated embeddings, reranking | Optional retrieval approaches; explicit Voyage vectors and Vector Search already satisfy this project's needs |
| LangChain / LangGraph / LangSmith | Optional libraries and tracing tools; the single-step agent does not need a workflow framework |
| Change streams, checkpoint/resume, GraphRAG | Relevant to other tracks or later expansion; not required for this track's demo |
| ElevenLabs | Optional voice integration and separate partner prize; no voice feature is currently justified |

## Concrete gaps before judging

1. Configure keys and confirm use of the event sandbox. Create the indexes, verify `queryable`, then seed. Setup now refuses to seed when the memory index times out.
2. Run the real-provider flip test. Do not adjust or fabricate replay outcomes to obtain a desired result.
3. Wire the dashboard to the existing API; its present controls and metrics use mock data.
4. Run one incident through retrieval, decision, replay, review, human approval, and fresh retrieval. Record actual actions and simulator snapshots.
5. Verify tenant isolation, expiry, quarantine, version links, and access logs against Atlas.
6. Review evidence lookup with the teammate: current fallback chooses the newest same-tenant evidence without checking service, and lookup does not explicitly require a nonempty `verified_by`. The seeded dataset has one verified checkout evidence record, but broader data needs stronger filtering.
7. Approval writes span multiple documents without a transaction. An insertion failure after quarantine can leave a partial correction; test the demo path and avoid claiming atomic approval.
8. Session identities are a demo picker, not authentication. Reset endpoints are demo utilities. Do not expose a shared write-enabled demo as a secure multi-user service.

## Submission checklist from page 3

- Use the event-issued Atlas Sandbox project and cluster.
- Submit through the Cerebral Valley platform by **5:00 PM Toronto time on November 14**.
- Include the public repository, a concise project description, and a **one-minute video** showing today's code and functionality.
- Verify video and audio playback; add every team member to the submission.
- Ensure the demo link is accessible and prepare the live in-person demonstration.

## Repository identity

Product: **RecallTrace**. Repository: [beanscrack/Recall-Trace](https://github.com/beanscrack/Recall-Trace). The owner renamed it during the live validation work.

Suggested GitHub description: "Agent memory governance with MongoDB Atlas, Vector Search, and counterfactual replay."

Suggested topics: `mongodb`, `mongodb-atlas`, `vector-search`, `agent-memory`, `ai-agents`, `counterfactual-replay`, `fastapi`, `react`, `hackathon`.

Renaming the GitHub repository or editing its About settings requires an owner/admin account. Keep the internal database namespace `memory_court` for existing deployments; a product rename does not require migrating or reseeding team data.

## Follow-up live validation

Atlas and Voyage are now configured in the local ignored `.env`. The backend supports an optional process-local DNS override because system DNS omitted valid Atlas SRV records. A fresh application connection passed, both vector indexes report READY/queryable with 1024 dimensions, and live Voyage document/query embeddings returned 1024 dimensions.

The strengthened isolation script passed all six live nonempty searches with tenant, active-status, and expiry assertions, plus both refused cross-tenant direct reads and their access logs. Voyage returned a 3-RPM limit during the first attempt; rerunning with `--interval 21` passed. No demo data was reset or reseeded.

Existing Atlas records show `disable_fraud_checks`, an approved correction, and a `rollback_deployment` rerun. Correction status, version links, reviewer metadata, and replacement embedding dimensions passed inspection. These stored records do not establish that a fresh run using the current local configuration passes. OpenAI gpt-4.1-mini is now configured locally, but the live preflight returns HTTP 429 / credit_balance_exhausted.

All 20 offline backend checks passed. Current task ownership and remaining work are tracked in [TASKS.md](TASKS.md).

A subsequent `demo_check.py` run passed live Atlas/Voyage API checks, session and tenant guards, refusal logging, and stored decision/replay/verdict serialization using in-process HTTP. All 22 offline checks passed, including failure regression tests confirming no simulated action or decision write after retrieval/LLM failure. The `--execute` path reports the billing blockage before touching demo data; fresh OpenAI replay remains unverified.
