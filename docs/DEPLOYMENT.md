# Run and publish RecallTrace

The API and built dashboard can run as one FastAPI service. MongoDB Atlas remains the memory, evidence, audit, and decision store. Use one worker because the checkout simulator is process-local.

## Current temporary demo

- App: https://hero-momentum-depot-floating.trycloudflare.com
- One-minute narrated video: https://hero-momentum-depot-floating.trycloudflare.com/demo.mp4

The public app and Atlas health endpoint returned HTTP 200, the complete browser workflow passed through this URL, and the video played with both audio/video decoding. These links depend on the local server and tunnel remaining running. They are temporary, not a persistent deployment; [Cloudflare Quick Tunnels have no uptime guarantee](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

To recreate the temporary deployment:

```bash
cd frontend
npm ci
npm run build
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal, with Cloudflare's `cloudflared` installed:

```bash
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```

Use the new URL printed by the tunnel; a recreated tunnel will usually have a different URL. The local ignored `.env` supplies all server credentials. Frontend bundles never contain those keys. A public request for `/.env` was verified to return 404.

The generated video is also saved in Windows Downloads as `RecallTrace-demo.mp4`. To serve a regenerated video, copy it to `frontend/dist/demo.mp4` after the frontend build; rebuilding clears that directory.

## Persistent deployment preparation

The repository includes a multistage `Dockerfile`, `.dockerignore`, and `render.yaml`. The Node stage builds the dashboard; the Python stage runs the existing FastAPI/PyMongo application. No architecture rewrite or secondary database is required.

When an account is available, create a [Render Blueprint](https://render.com/docs/blueprint-spec) from this public repository and enter the values marked `sync: false`:

- `MONGODB_URI` for the event-issued Atlas Sandbox.
- `VOYAGE_API_KEY`.
- `LLM_API_KEY` for OpenRouter.

The blueprint sets the provider, model, API base URL, and existing `memory_court` database name. For a local DNS problem, the optional `MONGODB_DNS_NAMESERVERS` setting remains available; do not assume another host needs it.

Do not reseed an existing shared Atlas database just to deploy. A seed/reset is a deliberate rehearsal operation, not a startup hook. Container startup serves the already built dashboard and API; it does not erase collections or indexes.

Validation limit: Docker Desktop is installed on the host but its Linux engine is not running/available to this WSL session. The image build has therefore **not** been executed here. The equivalent production entry point, built static assets, API, and public tunnel were tested successfully. Persistent hosting is prepared, not claimed deployed.

## GitHub About: owner-only step

The repository is public and named `beanscrack/Recall-Trace`. The connected account has push permission but `admin: false` and `maintain: false`, so it cannot change repository settings. The existing About text still uses the old name and claims proof of fixes. An owner can apply the prepared metadata:

```bash
gh repo edit beanscrack/Recall-Trace \
  --description 'RecallTrace: investigate AI memory influence, approve corrections, and verify changed decisions. Built with MongoDB Atlas and Voyage AI.' \
  --add-topic mongodb \
  --add-topic mongodb-atlas \
  --add-topic atlas-vector-search \
  --add-topic voyage-ai \
  --add-topic ai-agents \
  --add-topic agent-memory \
  --add-topic memory-governance \
  --add-topic counterfactual-replay \
  --add-topic fastapi \
  --add-topic react \
  --add-topic hackathon \
  --add-topic cerebral-valley
```

The same values are in `.github/repository-settings.json`. This file documents the desired settings; GitHub does not apply it automatically. Keep a permanent homepage unset until a persistent hosting URL exists.
