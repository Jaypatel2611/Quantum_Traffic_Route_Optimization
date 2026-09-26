# SIH26137 Phase 0 — Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the DDD-structured FastAPI backend and React+TypeScript frontend as separate Dockerized services, with pinned dependencies and a working health-check round trip, and zero algorithm logic.

**Architecture:** Two services (`backend/`, `frontend/`) composed via Docker Compose. Backend follows the Domain-Driven Design layout in PRD Section 18 (domain/application/infrastructure/presentation) with all algorithm/geospatial files present as empty stub modules — only `app/main.py`'s `/health` route and CORS middleware contain real logic. Frontend is a Vite+React+TS app whose only real logic is a `/health` fetch on mount.

**Tech Stack:** Python 3.11, FastAPI, pytest, httpx (backend); Node LTS, Vite, React, TypeScript, Vitest (frontend); Docker Compose.

**Spec:** `../../../SIH26137_Implementation_PRD.md` (Sections 7, 8, 18, 21) and `../../../SIH26137_Design_Brief.md`

## Global Constraints

- DDD folder layout exactly per PRD Section 18 — no renamed or added top-level packages.
- No Kubernetes, no Celery/Redis, no microservices split beyond backend/frontend (PRD A4, Section 21).
- Dependencies pinned by lock file generated from an actual installed environment (`pip freeze`, `package-lock.json`) — no floating `>=`/`^` ranges, no `latest` Docker tags (PRD Section 8, 21).
- CORS explicit and origin-scoped to `http://localhost:5173` — never `allow_origins=["*"]` (PRD Section 8).
- No algorithm logic in this phase — domain/application/infrastructure modules are structural stubs only (user's Phase 0 instruction).
- Tests written before/alongside the code they cover (TDD), not after.
- One commit per task, conventional format (`feat:`/`test:`/`docs:`).

## Review Focus

- Backend container that fails to bind `0.0.0.0` (only `127.0.0.1`) would be unreachable from the frontend container across the Compose network — verify `uvicorn` host binding.
- `/health` must stay responsive even though later phases add long-running solver work — a synchronous/blocking handler here would be a regression discovered late; keep it `async def` from the start.
- Frontend calling `http://localhost:8000` directly (hardcoded) breaks the moment the Compose service name differs from `localhost` — use an env-configurable API base URL.
- A missing `.dockerignore` would COPY `node_modules`/`.venv`/`.git` into images, bloating builds and risking stale-dependency drift the pinning step is meant to prevent.
- CORS misconfigured to `*` "just to get it working" during dev would silently violate the Global Constraint above and ship that way if nobody checks it again later.

---

### Task 1: Backend DDD skeleton + pinned dependencies

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/domain/entities/__init__.py`, `backend/app/domain/entities/vehicle.py`, `backend/app/domain/entities/node.py`, `backend/app/domain/entities/route.py`, `backend/app/domain/value_objects/__init__.py`, `backend/app/domain/value_objects/geographic_coordinates.py`, `backend/app/domain/value_objects/fitness_score.py`, `backend/app/domain/value_objects/co2_emission_profile.py`, `backend/app/domain/exceptions.py`
- Create: `backend/app/application/__init__.py`, `backend/app/application/services/__init__.py`, `backend/app/application/services/optimization_orchestrator.py`, `backend/app/application/interfaces/__init__.py`, `backend/app/application/interfaces/solver_port.py`, `backend/app/application/interfaces/geospatial_repository_port.py`
- Create: `backend/app/infrastructure/__init__.py`, `backend/app/infrastructure/algorithms/__init__.py`, `backend/app/infrastructure/algorithms/qpso_solver.py`, `backend/app/infrastructure/algorithms/or_tools_baseline.py`, `backend/app/infrastructure/algorithms/copert_model.py`, `backend/app/infrastructure/geospatial/__init__.py`, `backend/app/infrastructure/geospatial/osmnx_client.py`, `backend/app/infrastructure/geospatial/distance_matrix_builder.py`, `backend/app/infrastructure/geospatial/stochastic_delay_injector.py`
- Create: `backend/app/presentation/__init__.py`, `backend/app/presentation/api/__init__.py`, `backend/app/presentation/api/v1/__init__.py`, `backend/app/presentation/api/v1/optimize_router.py`, `backend/app/presentation/api/v1/scenario_router.py`, `backend/app/presentation/schemas/__init__.py`, `backend/app/presentation/schemas/optimize_request.py`, `backend/app/presentation/schemas/optimize_response.py`, `backend/app/presentation/sse/__init__.py`, `backend/app/presentation/sse/convergence_stream.py`
- Create: `backend/requirements.txt`, `backend/Dockerfile`, `backend/.dockerignore`
- Create: `cache/.gitkeep`, `tests/unit/.gitkeep`, `tests/property_based/.gitkeep`, `tests/integration/.gitkeep`

**Interfaces:**
- Produces: an installable `backend/app` package with every module import-able and empty (each non-`__init__.py` file contains only a module docstring naming which future phase fills it in, e.g. `"""QPSO solver — implemented in Phase 3."""`), plus `backend/requirements.txt` pinned to exact versions.

- [ ] **Step 1: Create the domain/application/infrastructure/presentation package tree**

Create every file listed above. Every non-`__init__.py` file gets exactly one line:

```python
"""Stub — implemented in Phase N. No logic yet (Phase 0 scaffolding only)."""
```

with `N` set per PRD Section 21's build order (entities/value_objects/exceptions → Phase 1–4 as each solver needs them; `optimization_orchestrator.py` → Phase 5; `qpso_solver.py` → Phase 3; `or_tools_baseline.py` → Phase 2; `copert_model.py` → Phase 4; `osmnx_client.py`/`distance_matrix_builder.py`/`stochastic_delay_injector.py` → Phase 1; `optimize_router.py`/`scenario_router.py`/schemas → Phase 6/7; `convergence_stream.py` → Phase 5). `__init__.py` files are empty (0 bytes).

**Step 2: Verify the package imports cleanly**

Run: `python -c "import app.domain.entities.vehicle, app.application.services.optimization_orchestrator, app.infrastructure.algorithms.qpso_solver, app.presentation.sse.convergence_stream"` from `backend/`
Expected: no output, exit code 0 (proves `__init__.py` placement and package structure are correct before any real code depends on it).

**Step 3: Install pinned backend dependencies**

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install fastapi "uvicorn[standard]" pydantic pytest httpx
.venv/Scripts/pip freeze > requirements.txt
```

(Only the four libraries this phase actually uses — `osmnx`/`ortools`/`numpy`/`networkx` are added in the phase that first imports them, per the Global Constraint against speculative dependencies.)

**Step 4: Add Dockerfile and .dockerignore**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```
# backend/.dockerignore
.venv
__pycache__
*.pyc
```

**Step 5: Commit**

```bash
git add backend cache/.gitkeep tests/unit/.gitkeep tests/property_based/.gitkeep tests/integration/.gitkeep
git commit -m "feat: scaffold backend DDD package structure and pin dependencies"
```

---

### Task 2: FastAPI app with CORS + `/health`

**Files:**
- Create: `backend/app/main.py`
- Test: `tests/integration/test_health.py`

**Interfaces:**
- Consumes: nothing from Task 1 (stub modules aren't imported by `main.py` yet).
- Produces: `app.main:app` (FastAPI instance) — later phases mount `optimize_router`/`scenario_router` onto this instance and add the SSE route.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_health.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../.venv/Scripts/pytest ../tests/integration/test_health.py -v` (or the venv created in Task 1)
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SIH26137 Quantum Traffic Route Optimization")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/integration/test_health.py
git commit -m "feat: add FastAPI app with CORS and /health endpoint

test: cover /health with an integration test"
```

---

### Task 3: Frontend Vite+React+TS skeleton + pinned dependencies

**Files:**
- Create: `frontend/` (Vite scaffold: `package.json`, `package-lock.json`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `vite.config.ts`)
- Create: `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/.env.development` (`VITE_API_BASE_URL=http://localhost:8000`)

**Interfaces:**
- Produces: `frontend/src/App.tsx` exporting a default `App` component that Task 4 modifies to call `/health`.

- [ ] **Step 1: Scaffold via Vite and pin exact versions**

```bash
cd /d/Jay/quantum_traffic_route_optimization
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

Then open `package.json` and strip every `^`/`~` prefix from `dependencies`/`devDependencies` so each is an exact version (matching what `package-lock.json` already resolved), and re-run `npm install` to confirm the lock file doesn't change.

- [ ] **Step 2: Add Vitest + Testing Library for Task 4's test**

```bash
npm install --save-exact --save-dev vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 3: Add Dockerfile and .dockerignore**

```dockerfile
# frontend/Dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
RUN npm install -g serve@14.2.1
COPY --from=build /app/dist ./dist
EXPOSE 4173
CMD ["serve", "-s", "dist", "-l", "4173"]
```

```
# frontend/.dockerignore
node_modules
dist
```

- [ ] **Step 4: Verify the scaffold builds**

Run: `npm run build`
Expected: exits 0, produces `frontend/dist/`

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold Vite React+TypeScript frontend and pin dependencies"
```

---

### Task 4: Frontend health-check round trip

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`
- Create: `frontend/vitest.config.ts` (or extend `vite.config.ts` with a `test` block)

**Interfaces:**
- Consumes: `GET {import.meta.env.VITE_API_BASE_URL}/health` → `{status: string}` (Task 2's contract).
- Produces: nothing consumed by a later task — this is the phase's demoable deliverable.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/App.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: "ok" }),
      } as Response)
    );
  });

  it("renders the backend health status after fetching it", async () => {
    render(<App />);
    await waitFor(() => screen.getByText(/backend status: ok/i));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run`
Expected: FAIL — no element with text `/backend status: ok/i` (App doesn't fetch yet)

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/App.tsx
import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState<string>("loading...");

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <div>
      <h1>SIH26137 — Quantum Traffic Route Optimization</h1>
      <p>Backend status: {status}</p>
    </div>
  );
}

export default App;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/vitest.config.ts
git commit -m "feat: fetch and render backend health status on load

test: cover App's health round trip with a mocked fetch"
```

---

### Task 5: Docker Compose wiring + manual round-trip verification

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Consumes: `backend/Dockerfile` (Task 1), `frontend/Dockerfile` (Task 3), the `/health` contract (Task 2/4).

- [ ] **Step 1: Write docker-compose.yml**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
  frontend:
    build: ./frontend
    ports:
      - "4173:4173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      - backend
```

- [ ] **Step 2: Bring both services up and verify the round trip**

Run: `docker compose up --build`
Then: `curl http://localhost:8000/health` → expect `{"status":"ok"}`
Then: open `http://localhost:4173` in a browser → expect "Backend status: ok" rendered.

Paste the terminal output of both the `curl` call and `docker compose up` (showing both containers healthy) into the phase summary — this is the "hello world round trip" deliverable the user asked to see.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: wire backend and frontend services via Docker Compose"
```

---

### Task 6: Explainability document (initialize)

**Files:**
- Create: `EXPLAINABILITY.md`

**Interfaces:**
- Produces: the running project-explainability log this and every later phase appends a summary section to.

- [ ] **Step 1: Write the initial file**

```markdown
# SIH26137 — Egreen Quanta: Build Explainability Log

Source of truth: `SIH26137_Implementation_PRD.md`, `SIH26137_Design_Brief.md`.
Updated after every phase and every noticeable change.

## Phase 0 — Scaffolding

**What was built:** DDD-structured FastAPI backend (`backend/app/{domain,application,infrastructure,presentation}`)
with stub modules for every Phase 1–7 file named in PRD Section 18; a Vite+React+TypeScript frontend;
Docker Compose wiring both; pinned dependencies in both `backend/requirements.txt` and `frontend/package-lock.json`.

**What was deliberately deferred:** all algorithm/geospatial logic (empty stub modules only, per this phase's explicit scope).

**How to verify:** `docker compose up --build`, then `curl http://localhost:8000/health` and load `http://localhost:4173`.

**Open questions/flags:** none.
```

- [ ] **Step 2: Commit**

```bash
git add EXPLAINABILITY.md
git commit -m "docs: initialize explainability log with Phase 0 summary"
```

---

## Self-Review Notes

- **Spec coverage:** repo structure (Section 18) → Task 1; FastAPI+CORS+health (Section 8, build-order step 1) → Task 2; frontend scaffold (Section 21) → Task 3–4; Docker Compose two-service round trip (Section 8, 21) → Task 5; explainability doc (user's cross-phase rule) → Task 6. No algorithm/geospatial/solver code included — correctly out of scope per the user's explicit Phase 0 instruction.
- **Placeholder scan:** stub files use a one-line docstring naming the exact future phase, not `TODO`/`TBD` — acceptable because "stub, no logic yet" *is* Phase 0's actual deliverable, not an unfinished plan step.
- **Type consistency:** `/health` response shape (`{"status": "ok"}`) is identical across Task 2's Python test, Task 4's mocked fetch, and Task 5's manual curl check.
- **Review Focus:** each of the five items above is addressed by an explicit step (host binding via `--host 0.0.0.0` in the Dockerfile CMD; `async def health`; `VITE_API_BASE_URL` env var instead of a hardcoded URL; `.dockerignore` in both services; CORS pinned to `localhost:5173` in Task 2, never `*`).
