# Verified results — November 14, 2026

Current provider: OpenRouter `nvidia/nemotron-3.5-super-vl:free`. Current embedding model: Voyage `voyage-4`, 1024 dimensions. Credentials stay in the ignored root `.env`.

## Checks that passed

| Check | What was actually verified |
| --- | --- |
| 34 offline Python tests | Replay/API behavior; failed agent requests; index readiness; optional DNS; same-service/newer/verified evidence filters; unavailable-index fallback; embedding cache isolation/retry; seed failure preserving data |
| Live Atlas evidence and transaction check | Normal-query fallback excludes wrong-service, blank-verifier, and older evidence. Real transactions roll back a failed replacement insert and a failed verdict update. Success commits quarantine, replacement, service/version links, and approval together. Embeddings are mocked only for these isolated transaction fixtures; fixtures are removed afterward |
| Full Super VL HTTP rehearsal | Reset/seed, unsafe agent action, contest, stable replay, stale-memory influence, PM-31 correction, named approval, version links, fresh rollback rerun, expiry/quarantine exclusion, Globex search, logged direct-read refusal |
| Complete public browser walkthrough | Real clicks through the same flow over the temporary HTTPS tunnel; Acme content disappears on tenant switch; no browser JavaScript errors. Uses real Atlas, Voyage, and LLM requests |
| Mocked browser failure states | Incomplete, unstable-baseline, and inconclusive results show accurate explanations and a retry control. Failed baseline calls display zero observed flips. These browser fixtures never write fabricated replay results into Atlas |
| Frontend build/lint | Production Vite build, TypeScript, and oxlint pass |
| Public deployment and video | Dashboard and Atlas health return HTTP 200; `/.env` returns 404; 60-second MP4 plays with audio and video decoding through the public tunnel |

The browser run measured `disable_fraud_checks` with simulated fraud at **7.1%** before correction and `rollback_deployment` with fraud at **0.4%** after fresh retrieval. Baseline stability was **100%**; removing stale INC-212 flipped the action in **3/3** trials; the other three ablations were **0/3**. These small repeated comparisons are evidence of influence, not statistical or causal proof. Exact IDs and actions are in [submission/validated-run.json](submission/validated-run.json).

Existing demo documents were backed up to an ignored, owner-readable local file before rehearsal resets. The live transaction check uses a unique temporary test tenant and removes its fixtures. Real rehearsal resets intentionally replace the demo dataset; do not run them during another developer's work without coordinating.

## Repeat the checks

From `backend/`, after installing runtime requirements:

```bash
.venv/bin/python -m unittest discover -s scripts -p '*_test.py' -v
.venv/bin/python scripts/court_transaction_check.py
```

Build the dashboard and run one API worker. The HTTP rehearsal **resets** demo data:

```bash
.venv/bin/python scripts/demo_rehearsal.py http://127.0.0.1:8000
```

Optional browser QA needs development dependencies and Chromium:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium --only-shell
.venv/bin/python scripts/browser_demo_check.py --reset --base-url http://127.0.0.1:8000
.venv/bin/python scripts/browser_states_check.py http://127.0.0.1:8000
```

Browser screenshots, raw recording, and response evidence go to ignored `.local/qa`. For the submission video, add `narration.wav` and the source-code screenshot `00-code.png`, then run `scripts/make_demo_video.py`. The generated MP4 is exactly 60 seconds and is decoded as a final integrity check.

## Limits and deferred items

- The public URL is a temporary tunnel and requires the local server/tunnel to remain running. Permanent deployment files are prepared; no permanent hosting account was used.
- Docker image build is untested because the host Docker Linux engine is unavailable. The production Python entry point and served frontend were tested directly.
- The simulator is process-local; the demo uses one worker. Sessions are demo identities, not authentication.
- GitHub About metadata still requires owner/admin access. The desired values and owner command are prepared.
- Final team/submission details and Sandbox-invitation confirmation were explicitly deferred by the user. The project has not been submitted to the competition.

## Legacy shared-seed compatibility

A final read found that the shared dataset had been reset by another process after the recorded browser run. The replacement records came from an older seeder without service tags. The court now recognizes service only for an exact canonical demo `seed_key` + tenant + text match when the tag is absent; changed or unknown legacy text still receives no corrective evidence. Newly approved replacements preserve the resolved service. Two additional offline checks verify these boundaries.

Historical run IDs in the archived JSON can return 404 after a deliberate demo reset. The saved measurements and video describe the recorded run; they are not fabricated replacements for current Atlas records.

The complete `demo_rehearsal.py --reuse-data` path also passed against the actual shared legacy dataset without reseeding Atlas. It explicitly verified that the approved version-2 memory was retrieved on the rollback rerun. Its actual IDs and measured results are preserved in [legacy-seed-run.json](submission/legacy-seed-run.json).
