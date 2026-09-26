import uuid

import numpy as np
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.presentation.sse.convergence_stream import convergence_event_stream

app = FastAPI(title="SIH26137 Quantum Traffic Route Optimization")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Explicitly temporary wiring -- no Pydantic validation (Phase 7's job at
# presentation/schemas/), not the real optimize_router.py/scenario_router.py
# (Phase 6/7's own stubs stay deferred). Exists only to prove the async/SSE
# mechanism over real HTTP for Phase 5's verification.
orchestrator = OptimizationOrchestrator()


@app.post("/jobs")
async def create_job(payload: dict, background_tasks: BackgroundTasks) -> dict:
    job_id = str(uuid.uuid4())
    seed = payload.pop("seed")
    time_budget_s = payload.pop("time_budget_s")
    payload["time_matrix"] = np.array(payload["time_matrix"], dtype=float)
    payload["distance_matrix"] = np.array(payload["distance_matrix"], dtype=float)
    background_tasks.add_task(orchestrator.run_comparison, job_id, payload, seed, time_budget_s)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    return StreamingResponse(
        convergence_event_stream(job_id, orchestrator), media_type="text/event-stream"
    )
