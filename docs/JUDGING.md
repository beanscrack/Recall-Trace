# Three-minute judging runbook

RecallTrace's strongest demonstration is a governed memory change that changes the next action. Atlas is essential to that chain: semantic retrieval, eligibility filtering, decision snapshots, replay measurements, verified evidence, transactional correction, and access logs.

## Eligibility first

The event resource guide requires the project and cluster to be created through the event-issued Atlas Sandbox invitation for finalist eligibility. A successful Atlas connection cannot establish that provenance. The user deferred confirmation; check the invitation/project in the organizer-provided account before final submission.

Use the public repository, the one-minute video, and an accessible demo link in the Cerebral Valley submission. Final team/member details and the actual submission remain deferred.

## Show, then explain

| Time | Action | Point to make |
| --- | --- | --- |
| 0:00–0:20 | Explain the checkout incident | Teams can correct an agent's code while its stored memory keeps repeating an unsafe runbook |
| 0:20–0:45 | Run the agent; show retrieved INC-212 and rising simulated fraud | The selected action used real Atlas retrieval and a real structured LLM tool call |
| 0:45–1:20 | Contest; show stable baseline and the highlighted removal row | Replay uses exact recorded inputs. Removing this memory changed the action in 3/3 observed trials; other removals did not |
| 1:20–1:55 | Show PM-31 evidence, named approval, and linked memory versions | Same tenant/service, newer verified evidence. One Atlas transaction quarantines the old memory and links the new version |
| 1:55–2:25 | Rerun; show before/after and version-2 memory | Fresh Atlas retrieval leads to rollback; simulated fraud is 7.1% before and 0.4% after in the recorded run |
| 2:25–2:50 | Switch to Globex; search and attempt direct Acme read | Tenant filtering happens inside Vector Search, and refused reads are recorded |
| 2:50–3:00 | Close on the customer value | Incident-response and platform teams can inspect which memory influenced a decision and approve a traceable repair |

The figures above are from the verified recorded demonstration, not promises about every stochastic run. All incident data and checkout outcomes are synthetic.

## Have one Atlas tab ready

Keep these views ready before starting; do not spend the demo navigating setup screens:

1. **Vector indexes:** `memory_vector_index` and `evidence_vector_index` READY/queryable, with 1024 dimensions. Memory filter fields are `tenant_id`, `status`, and `expires_at`.
2. **Memories:** use the IDs displayed in the current dashboard. Show old `quarantined` + `superseded_by` beside replacement `active` + `supersedes` + incremented `version` + matching `service`.
3. **Decisions/replays:** show the exact retrieved text snapshot, original action, measured baseline stability, ablation actions, and flip rates.
4. **Verdict/access log:** show reviewer identity/time, evidence link, and a refused cross-tenant read.

The document IDs in archived validation JSON describe those recorded runs. Demo reset intentionally clears live history, so use IDs from the current run in the Atlas UI.

## Technical depth that is already implemented

- Atlas Vector Search drives memory retrieval, with eligibility predicates inside the search and a live-field recheck after search-index lag.
- Voyage supplies query/document embeddings. Only query vectors are cached; tenant-specific search results are always fresh.
- Decision snapshots make single-step replay auditable without re-querying current memories or executing actions.
- Verified evidence is scoped to the same tenant/service and a newer date, including the normal-query fallback.
- Real Atlas transaction-failure tests verify rollback after both a failed replacement insert and a failed verdict write.
- The memory validator requires governance fields, and access logs persist retrieval/refusal events.

Repeated comparisons provide evidence of influence, not mathematical causation. The session picker is a demo identity mechanism, and the checkout simulator runs in one process. Explain those limits plainly if asked.

## Rehearsal discipline

Freeze the model, backend version, and data setup before judging. Have every developer pull the latest main. Avoid concurrent resets of the shared demo database during another person's demonstration. The public tunnel is temporary and needs its local server to remain running; the saved video is the backup artifact.

Prioritize a clean run and an understandable customer problem over adding more integrations. The chosen track's required memory/retrieval/governance loop is already present. Full test evidence and the measured run are in [VALIDATION.md](VALIDATION.md); deployment and video links are in [DEPLOYMENT.md](DEPLOYMENT.md).
