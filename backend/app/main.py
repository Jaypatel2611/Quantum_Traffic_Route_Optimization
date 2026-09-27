import uuid

import numpy as np
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.presentation.api.v1 import optimize_router, scenario_router
from app.presentation.api.v1.dependencies import orchestrator

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


# Explicitly temporary, unvalidated wiring -- kept exactly as Phase 5 built
# it (raw pre-built matrices, no Pydantic) for its own existing tests and
# scripts/verify_sse_live_stream.py. The real, Pydantic-validated job-
# creation path for the Setup screen's city+CSV flow is
# optimize_router.py's POST /jobs/from-nodes; both share the same
# `orchestrator` singleton (presentation/api/v1/dependencies.py), so a job
# created by either endpoint streams/resolves through the same
# /jobs/{id}/stream and /jobs/{id}/result.
@app.post("/jobs")
async def create_job(payload: dict, background_tasks: BackgroundTasks) -> dict:
    job_id = str(uuid.uuid4())
    seed = payload.pop("seed")
    time_budget_s = payload.pop("time_budget_s")
    payload["time_matrix"] = np.array(payload["time_matrix"], dtype=float)
    payload["distance_matrix"] = np.array(payload["distance_matrix"], dtype=float)
    background_tasks.add_task(orchestrator.run_comparison, job_id, payload, seed, time_budget_s)
    return {"job_id": job_id}


app.include_router(scenario_router.router)
app.include_router(optimize_router.router)
