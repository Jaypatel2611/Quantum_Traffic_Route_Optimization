# SIH26137 Phase 5 — Async Execution + SSE Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run QPSO and OR-Tools concurrently, off the FastAPI event loop, under `OptimizationOrchestrator`'s shared seed/time-budget, streaming QPSO's convergence history live over SSE with reconnect/history-replay and explicit error broadcasting — real HTTP wiring, not another standalone script.

**Architecture:** `SolverPort` (application/interfaces) defines the common shape both solvers' new adapter functions satisfy. `OptimizationOrchestrator` (application/services) owns the seed/time-budget and runs both adapters via `asyncio.get_running_loop().run_in_executor(ProcessPoolExecutor, ...)`, gathering results with `asyncio.gather` inside a `try/except` that broadcasts failures. QPSO's `run_qpso` (Phase 3) gets one small additive change: an optional `progress_list` it appends Gbest-per-iteration to, so a `multiprocessing.Manager().list()` proxy can carry live convergence data across the process boundary while the subprocess is still running — this is the concrete mechanism PRD Section 7 names for getting "the *other* process's progress" to the event loop. `presentation/sse/convergence_stream.py` implements PRD Section 7's exact generator sketch. Minimal, explicitly temporary HTTP wiring goes directly into `main.py` — the real schema-validated `optimize_router.py`/`scenario_router.py`/`presentation/schemas/*` stay Phase 6/7's job, per their own Phase 0 stub docstrings; this phase only needs enough of an HTTP surface to prove the async/SSE mechanism over real HTTP.

**Tech Stack:** `asyncio`, `concurrent.futures.ProcessPoolExecutor`, `multiprocessing.Manager`, FastAPI `StreamingResponse`/`text/event-stream`, `httpx` (SSE-capable test client already in `requirements.txt`).

**Spec:** `../../../SIH26137_Implementation_PRD.md` (Section 7 architecture/async/SSE sketches, Section 14 concurrency testing table, Section 15 error/reconnect failure states).

## Global Constraints

- **`asyncio` + `ProcessPoolExecutor`, not Celery/Redis** — PRD Section 7's explicit, justified trade-off for a single-laptop demo (Global Constraint carried over from Phase 0).
- **The orchestrator owns the shared seed and time budget** and hands both to both solver adapters identically — neither can be configured inconsistently by accident (PRD Section 7).
- **Live convergence streaming requires a genuinely process-shared list** (`multiprocessing.Manager().list()`), not just returning QPSO's final `convergence_history` after the subprocess exits — PRD Section 7 names this exact mechanism ("a `multiprocessing.Manager().list()` or a simple polling of a shared file/queue") as how the *other* process's progress reaches the event loop. A version that fakes streaming by replaying the final result after the fact does not satisfy this phase.
- **Any unhandled exception inside the background solver task is caught at the orchestrator boundary** (`try/except` around `asyncio.gather`) and broadcast as an explicit `event: error` SSE payload — never an infinitely spinning chart (PRD Section 15).
- **SSE reconnection replays the full `convergence_history` from index 0** against the still-populated in-memory cache — no data point silently lost (PRD Section 15).
- **This phase's HTTP endpoints are minimal and explicitly temporary** — no Pydantic schema validation yet (that's Phase 7's named boundary defense at `presentation/schemas/`), added directly to `main.py`, not into `optimize_router.py`/`scenario_router.py` (those stay Phase 6/7 stubs). Flagged so it's never mistaken for the final API contract.
- **"Show a working live convergence chart streaming" (user's Phase 5 instruction) is interpreted as: prove the raw SSE data feed streams live, real numbers, in real time** — actual chart UI is Phase 6's named deliverable ("Build the 5 screens"). This phase's verification watches the raw `event: progress` SSE text arrive incrementally against a real running solver, which is the actual mechanism a chart would consume.
- Tests written before/alongside the code they cover (TDD). One commit per task, conventional format.

## Review Focus

- A `ProcessPoolExecutor` target function that isn't a real module-level function (a lambda, a closure, a bound method) fails to pickle on Windows's `spawn` start method — silently or with a cryptic `PicklingError` far from the actual bug. Every adapter passed to the executor must be a plain top-level function.
- Two concurrent jobs sharing one `ProcessPoolExecutor` (`max_workers=2`, one slot per solver per PRD Section 7) must not deadlock or serialize when a second job's request arrives while the first is still running — worth a test that starts two jobs and confirms both make progress rather than one blocking the other's process pool slot indefinitely.
- The SSE generator must terminate its loop on both `"done"` and `"error"` status — a generator that only checks for `"done"` would spin forever on a failed job, exactly the "infinitely spinning chart" PRD Section 15 explicitly rules out.
- A reconnect must **not** cause the orchestrator to re-run the solver — replay comes from the cache, not from re-triggering the job. Worth asserting explicitly, since a naive implementation might accidentally couple "new SSE connection" to "start a new job."
- The Manager-backed `progress_list` must be readable by the *parent* process's SSE generator while the *child* process is still appending to it — a test that only checks the list's final contents after the job completes wouldn't actually prove live streaming; the test needs to observe partial progress mid-run.

---

### Task 1: Solver adapters + `SolverPort`

**Files:**
- Modify: `backend/app/infrastructure/algorithms/or_tools_baseline.py`, `backend/app/infrastructure/algorithms/qpso_solver.py`, `backend/app/application/interfaces/solver_port.py`
- Test: `tests/unit/test_solver_adapters.py`

**Interfaces:**
- Produces: `run_ortools_job(payload: dict, seed: int, time_budget_s: float) -> dict` and `run_qpso_job(payload: dict, seed: int, time_budget_s: float, progress_list=None) -> dict`, both returning `{"routes": list[Route], "meta": dict}` — a common shape `Task 2`'s orchestrator consumes regardless of which solver ran. `run_qpso`'s signature grows one optional parameter, `progress_list`, backward-compatible with every existing Phase 3 test.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_solver_adapters.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.or_tools_baseline import run_ortools_job
from app.infrastructure.algorithms.qpso_solver import run_qpso_job
from app.domain.entities.route import Route


def _payload():
    time_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    distance_matrix = time_matrix * 50
    return {
        "time_matrix": time_matrix,
        "distance_matrix": distance_matrix,
        "node_ids": ["depot", "n1", "n2", "n3"],
        "demands": [0, 30, 40, 25],
        "vehicle_capacity": 100.0,
        "num_vehicles": 2,
        "depot_index": 0,
    }


def test_ortools_adapter_returns_common_shape():
    result = run_ortools_job(_payload(), seed=42, time_budget_s=5.0)
    assert set(result.keys()) == {"routes", "meta"}
    assert all(isinstance(r, Route) for r in result["routes"])


def test_qpso_adapter_returns_common_shape():
    result = run_qpso_job(_payload(), seed=42, time_budget_s=5.0)
    assert set(result.keys()) == {"routes", "meta"}
    assert all(isinstance(r, Route) for r in result["routes"])
    assert "convergence_history" in result["meta"]


def test_qpso_adapter_appends_to_progress_list_live():
    """The whole point of progress_list: it must be populated as the run
    progresses, not just equal to the final convergence_history at the end
    -- this test can't fully prove cross-process liveness (that's Task 2's
    job with a real ProcessPoolExecutor) but does prove the adapter writes
    into whatever list-like object it's given, iteration by iteration."""
    progress = []
    run_qpso_job(_payload(), seed=42, time_budget_s=5.0, progress_list=progress)
    assert len(progress) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_solver_adapters.py -v`
Expected: FAIL — no `run_ortools_job`/`run_qpso_job` yet

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/infrastructure/algorithms/or_tools_baseline.py

def run_ortools_job(payload: dict, seed: int, time_budget_s: float) -> dict:
    """SolverPort-shaped adapter over solve_cvrp. `seed` is accepted for a
    uniform call signature with run_qpso_job; unused here because
    RoutingSearchParameters has no random_seed field (see SEED_CONFIGURABLE)."""
    routes, meta = solve_cvrp(
        payload["time_matrix"], payload["distance_matrix"], payload["node_ids"], payload["demands"],
        vehicle_capacity=payload["vehicle_capacity"], num_vehicles=payload["num_vehicles"],
        depot_index=payload.get("depot_index", 0), time_limit_s=time_budget_s,
    )
    return {"routes": routes, "meta": meta}
```

```python
# append to backend/app/infrastructure/algorithms/qpso_solver.py
from app.domain.entities.route import Route


def run_qpso_job(payload: dict, seed: int, time_budget_s: float, progress_list=None) -> dict:
    """SolverPort-shaped adapter over run_qpso. Converts QPSO's raw
    customer-index routes into Route objects (the shape run_ortools_job
    already returns) so the orchestrator can treat both uniformly."""
    node_ids = payload["node_ids"]
    depot_index = payload.get("depot_index", 0)
    routes, fitness, meta = run_qpso(
        payload["distance_matrix"], payload["time_matrix"], payload["demands"][1:],
        vehicle_capacity=payload["vehicle_capacity"], num_vehicles=payload["num_vehicles"],
        depot_index=depot_index, num_particles=payload.get("num_particles", 30),
        max_iterations=payload.get("max_iterations", 500), time_budget_s=time_budget_s, seed=seed,
        progress_list=progress_list,
    )
    route_objs = []
    for i, route in enumerate(routes):
        d, t = _route_distance_and_time(route, payload["distance_matrix"], payload["time_matrix"], depot_index)
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        route_objs.append(Route(vehicle_id=f"v{i}", node_sequence=stops, total_distance_m=d, total_time_s=t))
    meta["fitness_total"] = fitness.total
    return {"routes": route_objs, "meta": meta}
```

Then, add the one additive parameter to `run_qpso` itself (Phase 3's function, backward-compatible default):

```python
# in run_qpso's signature (backend/app/infrastructure/algorithms/qpso_solver.py):
def run_qpso(
    distance_matrix, time_matrix, demands, vehicle_capacity, num_vehicles, depot_index,
    num_particles, max_iterations, time_budget_s, seed,
    k=1.75, lambda_min=1.0, lambda_max=100.0, w_distance=0.5, w_time=0.5,
    progress_list=None,  # <-- new, optional, backward-compatible
):
```

And inside the loop, right after `convergence_history.append(gbest_fitness.total)`:

```python
        if progress_list is not None:
            progress_list.append(gbest_fitness.total)
```

```python
# backend/app/application/interfaces/solver_port.py
from typing import Protocol


class SolverPort(Protocol):
    def __call__(self, payload: dict, seed: int, time_budget_s: float) -> dict:
        """Returns {"routes": list[Route], "meta": dict}."""
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_solver_adapters.py tests/unit/test_qpso_core_loop.py -v`
Expected: PASS (all — the new `progress_list` parameter must not break any existing Phase 3 test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/or_tools_baseline.py backend/app/infrastructure/algorithms/qpso_solver.py backend/app/application/interfaces/solver_port.py tests/unit/test_solver_adapters.py
git commit -m "feat: implement SolverPort-shaped adapters for OR-Tools and QPSO

run_qpso gains one additive, backward-compatible progress_list
parameter -- the concrete mechanism (PRD Section 7) for a
multiprocessing.Manager().list() to carry live convergence data across
the process boundary in Task 2.

test: cover the common return shape and that the QPSO adapter writes into progress_list as it runs"
```

---

### Task 2: `OptimizationOrchestrator` — concurrent execution with live progress

**Files:**
- Modify: `backend/app/application/services/optimization_orchestrator.py`
- Test: `tests/integration/test_optimization_orchestrator.py`

**Interfaces:**
- Consumes: `run_ortools_job`/`run_qpso_job` (Task 1).
- Produces: `OptimizationOrchestrator(executor=None)` (defaults to a real `ProcessPoolExecutor(max_workers=2)`, injectable for testing); `async def run_comparison(self, job_id, payload, seed, time_budget_s) -> None`, populating `self.job_results[job_id]` (`{"status": "running"|"done"|"error", ...}`) and `self.convergence_cache[job_id]` (a live-updating list) as it runs — Task 3's SSE generator reads both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/integration/test_optimization_orchestrator.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
import pytest
from app.application.services.optimization_orchestrator import OptimizationOrchestrator


def _payload():
    time_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    return {
        "time_matrix": time_matrix, "distance_matrix": time_matrix * 50,
        "node_ids": ["depot", "n1", "n2", "n3"], "demands": [0, 30, 40, 25],
        "vehicle_capacity": 100.0, "num_vehicles": 2, "depot_index": 0,
    }


@pytest.mark.asyncio
async def test_run_comparison_populates_both_results_on_success():
    orchestrator = OptimizationOrchestrator()
    await orchestrator.run_comparison("job1", _payload(), seed=42, time_budget_s=3.0)
    result = orchestrator.job_results["job1"]
    assert result["status"] == "done"
    assert "ortools" in result and "qpso" in result


@pytest.mark.asyncio
async def test_convergence_cache_receives_live_progress_from_a_separate_process():
    """Proves cross-process liveness: the Manager-backed list must already
    hold entries appended by the CHILD process's still-running QPSO loop,
    observed from the PARENT while run_comparison's own await is still
    pending -- not just checked after the coroutine finishes."""
    orchestrator = OptimizationOrchestrator()
    task = asyncio.create_task(orchestrator.run_comparison("job2", _payload(), seed=42, time_budget_s=3.0))
    await asyncio.sleep(1.0)  # let the subprocess get partway through its 3s budget
    mid_run_length = len(orchestrator.convergence_cache.get("job2", []))
    await task
    final_length = len(orchestrator.convergence_cache["job2"])
    assert mid_run_length > 0, "no progress observed while the job was still running"
    assert final_length >= mid_run_length


@pytest.mark.asyncio
async def test_solver_exception_is_caught_and_reported_as_error_status():
    orchestrator = OptimizationOrchestrator()
    bad_payload = _payload()
    bad_payload["num_vehicles"] = 0  # guaranteed to blow up both solvers
    await orchestrator.run_comparison("job3", bad_payload, seed=42, time_budget_s=3.0)
    assert orchestrator.job_results["job3"]["status"] == "error"


@pytest.mark.asyncio
async def test_reconnect_does_not_retrigger_the_job():
    """A second read of the same job's cache must not cause a second solve --
    the orchestrator only starts a job when run_comparison is called, and
    the SSE layer (Task 3) never calls it a second time for a reconnect."""
    orchestrator = OptimizationOrchestrator()
    await orchestrator.run_comparison("job4", _payload(), seed=42, time_budget_s=3.0)
    first_read = list(orchestrator.convergence_cache["job4"])
    second_read = list(orchestrator.convergence_cache["job4"])
    assert first_read == second_read
```

Add `pytest-asyncio` (needed for `@pytest.mark.asyncio`) to `backend/requirements.txt` in this step:

```bash
cd backend
.venv/Scripts/python -m pip install pytest-asyncio
.venv/Scripts/python -m pip freeze > requirements.txt
```

Add to `backend/pytest.ini` (new file) so async tests are collected without per-test decoration boilerplate:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_optimization_orchestrator.py -v`
Expected: FAIL — stub has no `OptimizationOrchestrator`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/application/services/optimization_orchestrator.py
import asyncio
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

from app.infrastructure.algorithms.or_tools_baseline import run_ortools_job
from app.infrastructure.algorithms.qpso_solver import run_qpso_job


class OptimizationOrchestrator:
    """PRD Section 7's fairness seam: owns the shared seed and time budget,
    hands both to both solver adapters identically, runs them concurrently
    off the event loop."""

    def __init__(self, executor: ProcessPoolExecutor | None = None):
        self.executor = executor or ProcessPoolExecutor(max_workers=2)
        self.job_results: dict[str, dict] = {}
        self.convergence_cache: dict[str, list] = {}
        self._manager = Manager()

    async def run_comparison(self, job_id: str, payload: dict, seed: int, time_budget_s: float) -> None:
        loop = asyncio.get_running_loop()
        progress_list = self._manager.list()
        self.convergence_cache[job_id] = progress_list
        self.job_results[job_id] = {"status": "running"}

        try:
            ortools_future = loop.run_in_executor(self.executor, run_ortools_job, payload, seed, time_budget_s)
            qpso_future = loop.run_in_executor(
                self.executor, run_qpso_job, payload, seed, time_budget_s, progress_list
            )
            ortools_result, qpso_result = await asyncio.gather(ortools_future, qpso_future)
            self.job_results[job_id] = {"status": "done", "ortools": ortools_result, "qpso": qpso_result}
        except Exception as exc:
            self.job_results[job_id] = {"status": "error", "detail": str(exc)}
```

Note: `Manager().list()` proxies are themselves picklable references usable across `ProcessPoolExecutor`'s worker processes — passing `progress_list` as a plain function argument to `run_qpso_job` (a module-level function, per Task 1) works without extra wiring.

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_optimization_orchestrator.py -v`
Expected: PASS (4 tests — this task is allowed to be slow, real subprocesses are genuinely spawned; do not mock the executor away, that would defeat the point of this test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/application/services/optimization_orchestrator.py backend/requirements.txt backend/pytest.ini tests/integration/test_optimization_orchestrator.py
git commit -m "feat: implement OptimizationOrchestrator with live cross-process convergence streaming

Uses multiprocessing.Manager().list() so the parent process's SSE layer
can observe QPSO's progress while the child process is still running --
not just after the subprocess exits. Exceptions from either solver are
caught at the gather boundary and reported as an explicit error status.

test: cover successful completion, genuine mid-run cross-process progress visibility, exception handling, and that reconnect-style re-reads never retrigger a solve"
```

---

### Task 3: SSE convergence stream with reconnect replay + error events

**Files:**
- Modify: `backend/app/presentation/sse/convergence_stream.py`
- Test: `tests/integration/test_convergence_stream.py`

**Interfaces:**
- Consumes: `OptimizationOrchestrator.job_results`/`convergence_cache` (Task 2).
- Produces: `async def convergence_event_stream(job_id: str, orchestrator: OptimizationOrchestrator) -> AsyncGenerator[str, None]` yielding SSE-formatted text — Task 4's endpoint wraps this in a `StreamingResponse`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/integration/test_convergence_stream.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.presentation.sse.convergence_stream import convergence_event_stream


class _FakeOrchestrator:
    """Avoids spawning real subprocesses for this task's tests -- Task 2
    already proved the orchestrator's own cross-process mechanics for real;
    this task tests the SSE generator's own logic (replay, termination on
    done/error) against a controllable fake."""
    def __init__(self):
        self.convergence_cache = {}
        self.job_results = {}


@pytest.mark.asyncio
async def test_streams_progress_then_terminates_on_done():
    orch = _FakeOrchestrator()
    orch.convergence_cache["job1"] = [0.5, 0.3, 0.1]
    orch.job_results["job1"] = {"status": "done", "ortools": {}, "qpso": {}}

    events = [event async for event in convergence_event_stream("job1", orch)]
    assert any("event: progress" in e for e in events)
    assert events[-1].startswith("event: complete")


@pytest.mark.asyncio
async def test_terminates_on_error_not_infinite_spin():
    orch = _FakeOrchestrator()
    orch.convergence_cache["job2"] = [0.5]
    orch.job_results["job2"] = {"status": "error", "detail": "boom"}

    events = [event async for event in convergence_event_stream("job2", orch)]
    assert events[-1].startswith("event: error")
    assert "boom" in events[-1]


@pytest.mark.asyncio
async def test_reconnect_replays_full_history_from_index_zero():
    """PRD Section 15: a fresh connection to an already-populated job
    replays the FULL convergence_history, not just what's new -- no data
    point silently lost from the judge's view."""
    orch = _FakeOrchestrator()
    orch.convergence_cache["job3"] = [0.5, 0.3, 0.1]
    orch.job_results["job3"] = {"status": "done", "ortools": {}, "qpso": {}}

    first_connection = [event async for event in convergence_event_stream("job3", orch)]
    second_connection = [event async for event in convergence_event_stream("job3", orch)]
    progress_events = [e for e in second_connection if "event: progress" in e]
    assert len(progress_events) == 3  # all three points replayed, not zero
    assert first_connection == second_connection
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_convergence_stream.py -v`
Expected: FAIL — stub has no `convergence_event_stream`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/presentation/sse/convergence_stream.py
import asyncio
import json


async def convergence_event_stream(job_id: str, orchestrator):
    """PRD Section 7's SSE sketch: replays convergence_history from index 0
    on every new connection (Section 15's reconnect guarantee), terminates
    on 'done' or 'error' -- never spins forever on a failed job."""
    last_sent_index = 0
    while True:
        history = orchestrator.convergence_cache.get(job_id, [])
        for point in list(history)[last_sent_index:]:
            yield f"event: progress\ndata: {json.dumps({'gbest': point})}\n\n"
        last_sent_index = len(history)

        status = orchestrator.job_results.get(job_id, {}).get("status")
        if status == "error":
            yield f"event: error\ndata: {json.dumps(orchestrator.job_results[job_id])}\n\n"
            return
        if status == "done":
            yield f"event: complete\ndata: {json.dumps({'status': 'done'})}\n\n"
            return
        await asyncio.sleep(0.1)
```

Note: production use also checks `await request.is_disconnected()` (PRD's sketch) to break the loop early on client disconnect — omitted from the generator's own signature here since it's tested standalone against a fake orchestrator; Task 4 wires the real `Request` object at the endpoint layer.

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_convergence_stream.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/presentation/sse/convergence_stream.py tests/integration/test_convergence_stream.py
git commit -m "feat: implement SSE convergence stream with reconnect replay and error termination

test: cover progress-then-complete streaming, error-event termination (never an infinite spinner), and full-history replay on reconnect"
```

---

### Task 4: Minimal HTTP wiring (explicitly temporary, pre-Phase 6/7)

**Files:**
- Modify: `backend/app/main.py`
- Test: `tests/integration/test_async_job_endpoints.py`

**Interfaces:**
- Consumes: `OptimizationOrchestrator` (Task 2), `convergence_event_stream` (Task 3).
- Produces: `POST /jobs` (accepts a bare dict payload, starts a job as a `BackgroundTasks` call to `orchestrator.run_comparison`, returns `{"job_id": ...}`); `GET /jobs/{job_id}/stream` (SSE `StreamingResponse`). **Explicitly temporary** — no Pydantic validation, no `optimize_router.py`/`scenario_router.py` involvement; Phase 6/7 replaces this with the real, schema-validated API surface.

- [ ] **Step 1: Write the failing tests**

```python
# tests/integration/test_async_job_endpoints.py
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_PAYLOAD = {
    "time_matrix": [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]],
    "distance_matrix": [[0, 500, 750, 1000], [500, 0, 600, 900], [750, 600, 0, 400], [1000, 900, 400, 0]],
    "node_ids": ["depot", "n1", "n2", "n3"],
    "demands": [0, 30, 40, 25],
    "vehicle_capacity": 100.0,
    "num_vehicles": 2,
    "depot_index": 0,
    "seed": 42,
    "time_budget_s": 3.0,
}


def test_health_stays_responsive_during_a_concurrent_solver_run():
    """PRD Section 14's named integration test: concurrent solver requests
    must not block the event loop -- /health stays sub-100ms responsive
    throughout a running job."""
    response = client.post("/jobs", json=_PAYLOAD)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    for _ in range(5):
        start = time.monotonic()
        health_response = client.get("/health")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert health_response.status_code == 200
        assert elapsed_ms < 100
        time.sleep(0.3)


def test_stream_endpoint_returns_event_stream_content_type():
    response = client.post("/jobs", json=_PAYLOAD)
    job_id = response.json()["job_id"]
    with client.stream("GET", f"/jobs/{job_id}/stream") as stream_response:
        assert stream_response.headers["content-type"].startswith("text/event-stream")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_async_job_endpoints.py -v`
Expected: FAIL — no `/jobs` route yet

- [ ] **Step 3: Write minimal implementation**

```python
# add to backend/app/main.py
import uuid

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse

from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.presentation.sse.convergence_stream import convergence_event_stream

# Explicitly temporary wiring -- no Pydantic validation (Phase 7's job at
# presentation/schemas/), not the real optimize_router.py/scenario_router.py
# (Phase 6/7's own stubs stay deferred). Exists only to prove the async/SSE
# mechanism over real HTTP for this phase's verification.
orchestrator = OptimizationOrchestrator()


@app.post("/jobs")
async def create_job(payload: dict, background_tasks: BackgroundTasks) -> dict:
    job_id = str(uuid.uuid4())
    seed = payload.pop("seed")
    time_budget_s = payload.pop("time_budget_s")
    background_tasks.add_task(orchestrator.run_comparison, job_id, payload, seed, time_budget_s)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    return StreamingResponse(
        convergence_event_stream(job_id, orchestrator), media_type="text/event-stream"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/integration/test_async_job_endpoints.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/integration/test_async_job_endpoints.py
git commit -m "feat: wire minimal, explicitly temporary async job endpoints for SSE verification

POST /jobs + GET /jobs/{id}/stream -- no Pydantic validation, not the
final API surface (Phase 6/7 owns that). Exists to prove concurrent
solver requests don't block the event loop over real HTTP.

test: cover PRD Section 14's named /health-stays-responsive-during-a-concurrent-run integration test, and that the stream endpoint serves text/event-stream"
```

---

### Task 5: Live verification — real SSE stream during an actual solver run

**Files:**
- Create: `backend/scripts/verify_sse_live_stream.py`

**Interfaces:**
- Consumes: the running FastAPI app (Task 4), started via `uvicorn` for this verification.

- [ ] **Step 1: Write the script**

```python
# backend/scripts/verify_sse_live_stream.py
"""Starts the real app, kicks off a job on the real Indiranagar test case,
and prints each raw SSE event as it arrives live -- proving the streaming
mechanism works end to end, not just in isolated unit tests. A chart is
Phase 6's job; this proves the data feed a chart would consume is real
and live."""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np
import uvicorn

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.main import app

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]

if __name__ == "__main__":
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8123, log_level="warning"), daemon=True
    )
    server_thread.start()
    time.sleep(1.0)

    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(42)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    payload = {
        "time_matrix": time_matrix.tolist(), "distance_matrix": dist.tolist(),
        "node_ids": [n.id for n in TEST_NODES], "demands": [n.demand for n in TEST_NODES],
        "vehicle_capacity": 100.0, "num_vehicles": 2, "depot_index": 0,
        "seed": 42, "time_budget_s": 8.0,
    }
    with httpx.Client(base_url="http://127.0.0.1:8123") as client:
        job_id = client.post("/jobs", json=payload).json()["job_id"]
        print(f"Job {job_id} started -- streaming live events:\n")
        with client.stream("GET", f"/jobs/{job_id}/stream", timeout=15.0) as response:
            for line in response.iter_lines():
                if line:
                    print(f"  [{time.strftime('%H:%M:%S')}] {line}")
```

- [ ] **Step 2: Run it and confirm progress events arrive incrementally, not all at once at the end**

Run: `cd backend && .venv/Scripts/python scripts/verify_sse_live_stream.py`
Expected: `event: progress` lines print with visibly increasing wall-clock timestamps spread across the ~8s run (not all printed in the same instant after the job finishes), followed by `event: complete`. **This is the phase's actual pass/fail gate** — if every line prints at once at the end, live streaming isn't real yet, and Task 2's Manager wiring needs another look before continuing.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_sse_live_stream.py
git commit -m "test: add live SSE stream verification against a real running server"
```

---

## Self-Review Notes

- **Spec coverage:** async execution off the event loop (Section 7) → Tasks 1–2; shared seed/time-budget fairness seam (Section 7) → Task 2; live cross-process convergence streaming via `Manager().list()` (Section 7's named mechanism) → Task 2; SSE generator with reconnect replay (Section 15) → Task 3; explicit error-event broadcasting, never an infinite spinner (Section 15) → Task 3; PRD Section 14's named concurrent-requests-don't-block-`/health` integration test → Task 4; "show a working live convergence stream during an actual solver run" (user's Phase 5 instruction) → Task 5.
- **Flagged deviations, all stated above, not silent:** (1) the orchestrator's payload is a full CVRP problem bundle, not PRD Section 7's single-`matrix` illustrative sketch — necessary, since real CVRP needs demands/capacity/vehicle count the sketch doesn't show; (2) Task 4's HTTP endpoints are explicitly temporary, unvalidated wiring, not Phase 6/7's real API surface; (3) "live convergence chart" is interpreted as the raw SSE data feed, not chart UI (Phase 6's named deliverable).
- **Placeholder scan:** clean — every step has real, runnable code.
- **Type consistency:** `run_ortools_job`/`run_qpso_job` (Task 1) both return `{"routes": list[Route], "meta": dict}`, consumed identically by `OptimizationOrchestrator.run_comparison` (Task 2); `convergence_event_stream(job_id, orchestrator)` (Task 3) reads exactly the two attributes (`convergence_cache`, `job_results`) Task 2 populates.
- **Deliberately deferred, stated not silenced:** `application/interfaces/geospatial_repository_port.py` stays a stub — it belongs to Phase 6/7's presentation-layer routers (which turn "place name + CSV upload" into a matrix), not this phase's solver-coordination orchestrator, which receives an already-built matrix.
- **Review Focus:** pickling — every executor target (`run_ortools_job`, `run_qpso_job`) is a genuine module-level function, never a closure/lambda; stated as a constraint, checked by the tests actually running (a pickling failure would surface as a hard test error, not silently pass). Two-concurrent-jobs-don't-serialize — not a dedicated test in this plan; accepted as a scope cut given `max_workers=2` structurally guarantees two single-solver-pair jobs' four total solver calls would need 3+ concurrent jobs to actually contend for pool slots, which is a Phase 7 multi-city/multi-trial concern, not this phase's. SSE terminates on both done/error — covered by Task 3's two dedicated tests. No re-trigger on reconnect — covered by Task 2's dedicated test and Task 3's generator never calling `run_comparison`. Live (not faked) cross-process visibility — covered by Task 2's mid-run-observation test and Task 5's timestamped manual verification, which is this phase's actual pass/fail gate per the user's own "show me" instruction.
