# Optional pairwise replay

Pair investigation is retained as an optional backend API feature, but its
controls and results are removed from the demo UI at the team's request. The
judge demo uses single-memory replay only. Normal replay requests do not run
pairs. The API supports snapshots containing 2–4 memories.

`POST /api/decisions/{decision_id}/replay?include_pairs=true` uses the existing
tenant ownership guard and repeats the recorded baseline and all single-memory
variants. Only a stable, error-free, inconclusive single-memory result escalates
to all unordered pairs. With four memories there are at most 33 calls: 3 baseline,
12 single-memory, and 18 pair calls. This is not similarity-guided selection;
no embeddings or new retrieval requests are needed.

Every variant retains the recorded prompt, model configuration, task, tools,
and snapshot order. No tool actions or simulator operations execute. Results
are persisted in the existing replays collection, linked to decision and tenant.

The additive `pairs` object contains `selection: all_pairs`, `status`,
`ablations` (removed_memory_ids, actions, errors, flip_rate), and
`candidate_memory_ids`. Its status is `not_run`, `incomplete`,
`no_clear_influence`, or `group_influence_detected`. A unique highest rate of at
least 2/3 is required; any pair error prevents attribution. Failed calls remain
null and never count as flips. All scheduled trials remain in the denominator.
The top-level status continues to describe single-memory findings.

Pair findings never populate `culprit_memory_id`. They indicate group influence,
not proof of interaction, causal dependence, or incorrectness of both memories.
The current correction workflow remains single-memory only; pair-based evidence
review and correction are not implemented. Removing all memories in a two-memory
snapshot should be interpreted especially cautiously as loss of the full context.

Validation: 44 offline backend tests pass, including 10 new pair tests. Browser
fixtures verify escalation, result retention between tabs, and absence of
single-memory correction controls for pair-only findings at desktop/mobile sizes.
A live Atlas/provider pair experiment also passed on a real corrected decision:
33 successful calls, all six pair variants, unchanged simulator state, and verified
persistence. All pair flip rates were 0%, yielding `no_clear_influence`, which is
valid for that corrected context. It took about 120 seconds. Positive group
attribution remains covered by mocked tests; this run does not demonstrate a
positive live group-influence finding. Raw results are archived locally in
`.local/qa/live-pairs-results.json`; demo resets clear their original Atlas history.
