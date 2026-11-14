# Three-minute judging runbook

RecallTrace's strongest demonstration is a governed memory change that changes the next action. Atlas is essential to that chain: semantic retrieval, eligibility filtering, decision snapshots, replay measurements, verified evidence, transactional correction, and access logs.

## Eligibility first

The event resource guide requires the project and cluster to be created through the event-issued Atlas Sandbox invitation for finalist eligibility. A successful Atlas connection cannot establish that provenance. Confirm the invitation/project in the organizer-provided account before final submission.

Use the public repository, the one-minute video, and an accessible demo link in the Cerebral Valley submission. Final team/member details and the actual submission still need to be completed.

## Show, then explain

| Time | Action | Point to make |
| --- | --- | --- |
| 0:00–0:20 | Explain the problem | Agents can repeat mistakes because they remember outdated advice. RecallTrace investigates and governs that memory |
| 0:20–0:40 | Run incident | Checkout errors rise after a deployment; an old runbook recommends disabling fraud checks |
| 0:40–1:00 | Inspect the actual decision; contest it | Show retrieved memory IDs, selected tool, and simulated fraud increase |
| 1:00–1:35 | Replay memories | Explain the exact snapshot and repeated comparisons while calls run; show measured stability and flips |
| 1:35–2:00 | Review correction; approve; start rerun | Same-tenant/service newer verified evidence; one transaction quarantines and replaces the memory |
| 2:00–2:20 | Compare outcomes | Show the actual action change, simulated rates, and replacement retrieved |
| 2:20–2:35 | Check isolation | Switch to Globex, search, and attempt a direct Acme read |
| 2:35–2:50 | Prepared Atlas view | Show old/new memory versions and links; explain Voyage embeddings and Atlas retrieval |
| 2:50–3:00 | Close | Investigate the memory, approve the fix, verify the next decision |


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

## Keep the presentation focused

Use the six tabs; one step is visible at a time. You can revisit results without
rerunning calls. The optional pairwise API is not exposed in the demo UI and
should not be triggered during this presentation: a measured run took about two
minutes. Explain Voyage's embedding role during retrieval rather than navigating
another dashboard.

Live provider latency may exceed the time budget. Rehearse with a stopwatch and
keep a clearly labeled recorded fallback ready. If switching to it, tell judges.
The existing video shows an earlier UI revision; the updated recording script is
in [submission/VIDEO_SCRIPT.md](submission/VIDEO_SCRIPT.md).
