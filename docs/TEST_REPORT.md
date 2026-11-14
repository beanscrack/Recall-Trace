# Demo validation — November 14, 2026

## Automated checks

- 44 offline backend tests passed, including pairwise attribution, failures,
  baseline gating, ties, thresholds, tenant refusal, and snapshot preservation.
- TypeScript/Vite production build and frontend lint passed.
- Python compilation and `git diff --check` passed.
- Browser tab navigation, Previous/Next, keyboard controls, and preserved-case
  layouts passed at 1440px, 390px, and 320px. Completed cases used archived
  responses intercepted in the browser, not fabricated Atlas records.
- Mocked incomplete, unstable, and inconclusive replay states passed.
- Mocked pair escalation/results passed at desktop and mobile widths, including
  absence of correction controls for pair-only findings.

## Real integrations

- Both Atlas Vector Search indexes were READY and queryable.
- Live Atlas transaction tests passed: evidence eligibility, no-write embedding
  failure, rollback after partial correction writes, and atomic success.
  Embeddings were mocked only for these transaction tests; fixtures were removed.
- Real browser walkthrough passed: seed/reset, Voyage retrieval, unsafe model
  action, stable replay attribution, verified correction proposal, human approval,
  fresh retrieval, rollback action, Globex-only search, and logged cross-tenant
  read refusal. No browser JavaScript errors were observed.
- Real pair replay on a corrected decision completed 33 provider calls and six
  pair variants, persisted results to Atlas, and left the simulator unchanged.
  All six flip rates were 0%; result `no_clear_influence`. Runtime ~120 seconds.
  Positive group attribution is tested with mocks, not demonstrated by this live
  run. See PAIRWISE_REPLAY.md for limitations.

## Fix found during validation

The persistent tab layout left the isolation form's initial memory ID empty when
an agent decision arrived later. Keying the form by the current case memory now
initializes the correct ID. The live browser test explicitly asserts that ID,
and waits for reset completion before starting the agent.

## Artifacts and scope

Current data was backed up before reset under `.local/backups/` (ignored,
restricted file permissions). Browser evidence and pair results are under
`.local/qa/`. Full rehearsals reset shared demo history; archived IDs can therefore
be absent from the latest Atlas dataset. No claim is made that external providers
will always return identical decisions. Pair testing is optional and adds enough
latency that it should not be required for the three-minute presentation.
