# SIH26137 — Egreen Quanta: Build Explainability Log

Source of truth: `SIH26137_Implementation_PRD.md`, `SIH26137_Design_Brief.md`.
Updated after every phase and every noticeable change.

## Phase 0 — Scaffolding

**What was built:**
- DDD-structured FastAPI backend (`backend/app/{domain,application,infrastructure,presentation}`) with stub modules for every Phase 1–7 file named in PRD Section 18, each docstring-tagged with the phase that fills it in.
- `backend/app/main.py`: FastAPI app with CORS middleware and an async `/health` endpoint, covered by an integration test.
- A Vite+React+TypeScript frontend (`frontend/`) whose `App.tsx` fetches `/health` on mount and renders the live status, covered by a mocked-fetch component test.
- `docker-compose.yml` wiring both services; both build and run via `docker compose up --build`.
- Dependencies pinned to exact resolved versions in both `backend/requirements.txt` (via `pip freeze`) and `frontend/package.json`/`package-lock.json` (stripped of `^`/`~` ranges).
- A dedicated git repository for this project (previously nested inside an unrelated personal monorepo) and a GitHub remote (`Jaypatel2611/Quantum_Traffic_Route_Optimization`) pushed after every task.

**What was deliberately deferred:** all algorithm/geospatial logic (empty stub modules only), per this phase's explicit scope.

**Bugs caught and fixed during this phase's own verification (not silently patched over):**
1. `docker-compose.yml`'s `environment: VITE_API_BASE_URL=...` on the frontend service was a no-op — Vite bakes `import.meta.env.*` values in at `npm run build` time, not container runtime, so a compose-level env var can never reach an already-built static bundle. Fixed by adding `frontend/.env.production` (read at build time inside the Dockerfile's `RUN npm run build` step) and removing the dead compose key.
2. A `curl` against `/health` returned `200 {"status":"ok"}`, but the actual browser page at `http://localhost:4173` showed "Backend status: unreachable" — curl doesn't enforce CORS, browsers do. The backend's `allow_origins` only listed the Vite dev-server origin (`:5173`), not the Compose-served demo origin (`:4173`), so the browser silently discarded the (successful, 200-logged) response before JS could read it. Caught by actually loading the page in a browser and reading network/console state, not by curl alone. Fixed by adding `:4173` to `allow_origins`, with a regression test (`test_health_allows_cors_from_docker_compose_frontend_origin`) confirmed RED before the fix and GREEN after.

**How to verify:** `docker compose up --build`, then `curl http://localhost:8000/health` and load `http://localhost:4173` in a browser — expect "Backend status: ok".

**Open questions/flags:** none.
