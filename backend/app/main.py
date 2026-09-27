import dataclasses
import uuid
from pathlib import Path

import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.algorithms.copert_model import co2_reduction_percent, total_emissions_kg
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.presentation.sse.convergence_stream import convergence_event_stream

app = FastAPI(title="SIH26137 Quantum Traffic Route Optimization")

# Explicitly temporary, per Phase 5's own convention: real Pydantic-validated
# scenario/optimize routers are reserved for a later phase (see
# presentation/schemas/ stub docstrings). Only one city is actually cached
# today -- data-driven so a second cache_path entry is the only change needed
# to add one, never a UI hardcode.
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
CITY_CATALOG = {
    "indiranagar_bengaluru": {
        "name": "Indiranagar, Bengaluru",
        "cache_path": CACHE_DIR / "indiranagar_bengaluru.graphml",
    },
}

FUEL_CO2_FACTOR_KG_PER_LITER = 2.68
"""Diesel combustion: ~2.68 kg CO2 per liter burned (standard IPCC/EPA
default road-transport factor, the same family this project's COPERT-proxy
already relies on) -- used only to convert an already-computed CO2 delta
into a liters-saved figure, never as an independent emissions source."""

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


@app.get("/cities")
async def list_cities() -> list[dict]:
    return [{"id": city_id, "name": info["name"]} for city_id, info in CITY_CATALOG.items()]


@app.post("/jobs/from-nodes")
async def create_job_from_nodes(payload: dict, background_tasks: BackgroundTasks) -> dict:
    """Bridges the Setup screen's city + CSV-upload flow to the existing
    matrix-based orchestrator -- explicitly temporary/unvalidated wiring in
    the same spirit as create_job above, not the real Phase-7 scenario
    router. `payload["nodes"][0]` is treated as the depot, per this
    project's existing node_ids[0]="depot" convention."""
    city = CITY_CATALOG.get(payload["city_id"])
    if city is None:
        raise HTTPException(status_code=404, detail=f"unknown city_id: {payload['city_id']!r}")

    nodes = [
        Node(
            id=n["id"],
            coordinates=GeographicCoordinates(lat=n["lat"], lon=n["lon"]),
            demand=n.get("demand", 0.0),
        )
        for n in payload["nodes"]
    ]
    graph = load_cached_graph(city["cache_path"])
    distance_matrix, base_time_matrix = build_distance_time_matrix(graph, nodes)
    seed = payload["seed"]
    rng = np.random.default_rng(seed)
    time_matrix = inject_stochastic_delay(base_time_matrix, rng, hour_of_day=payload.get("hour_of_day", 8.0))

    job_id = str(uuid.uuid4())
    job_payload = {
        "time_matrix": time_matrix,
        "distance_matrix": distance_matrix,
        "node_ids": [n.id for n in nodes],
        "demands": [n.demand for n in nodes],
        "vehicle_capacity": payload["vehicle_capacity"],
        "num_vehicles": payload["num_vehicles"],
        "depot_index": payload.get("depot_index", 0),
    }
    background_tasks.add_task(
        orchestrator.run_comparison, job_id, job_payload, seed, payload["time_budget_s"]
    )
    return {"job_id": job_id}


def _route_to_dict(route) -> dict:
    return dataclasses.asdict(route)


@app.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str) -> dict:
    result = orchestrator.job_results.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown job_id: {job_id!r}")
    if result["status"] != "done":
        return {"status": result["status"], "detail": result.get("detail")}

    ortools_routes = result["ortools"]["routes"]
    qpso_routes = result["qpso"]["routes"]
    ortools_co2_kg = total_emissions_kg(ortools_routes)
    qpso_co2_kg = total_emissions_kg(qpso_routes)
    ortools_time_s = sum(r.total_time_s for r in ortools_routes)
    qpso_time_s = sum(r.total_time_s for r in qpso_routes)
    co2_saved_kg = ortools_co2_kg - qpso_co2_kg

    return {
        "status": "done",
        "ortools": {
            "routes": [_route_to_dict(r) for r in ortools_routes],
            "meta": result["ortools"]["meta"],
            "total_co2_kg": ortools_co2_kg,
            "total_time_s": ortools_time_s,
        },
        "qpso": {
            "routes": [_route_to_dict(r) for r in qpso_routes],
            "meta": result["qpso"]["meta"],
            "total_co2_kg": qpso_co2_kg,
            "total_time_s": qpso_time_s,
        },
        "green_impact": {
            "co2_saved_kg": co2_saved_kg,
            "co2_reduction_percent": co2_reduction_percent(ortools_co2_kg, qpso_co2_kg),
            "fuel_saved_liters": co2_saved_kg / FUEL_CO2_FACTOR_KG_PER_LITER,
            "time_saved_s": ortools_time_s - qpso_time_s,
            "emission_factor_source": (
                "EMEP/EEA Guidebook COPERT formula (European-fleet-calibrated; "
                "India-specific ARAI/CPCB coefficients not yet available -- V2 dependency). "
                f"Fuel-saved liters derived from the CO2 delta via a standard "
                f"{FUEL_CO2_FACTOR_KG_PER_LITER} kgCO2/liter diesel combustion factor "
                "(IPCC/EPA default), not an independent measurement."
            ),
        },
    }
