import dataclasses
import uuid

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.application.services.green_impact_calculator import algorithm_result_payload, compute_green_impact
from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.domain.entities.node import Node
from app.domain.exceptions import UnknownCityError
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.presentation.api.v1.dependencies import get_geospatial_repository, get_orchestrator
from app.presentation.schemas.optimize_request import CreateJobFromNodesRequest
from app.presentation.schemas.optimize_response import CreateJobResponse, JobResultResponse
from app.presentation.sse.convergence_stream import convergence_event_stream

router = APIRouter()

# job_id -> {"from_node_id": int, "to_node_id": int}, for jobs created with
# an accident_edge -- a presentation-layer concern (Results' "re-route
# triggered by accident" caption), not the orchestrator's, so it's kept
# here rather than added to OptimizationOrchestrator's own state.
_accident_edges: dict[str, dict] = {}


@router.post("/jobs/from-nodes", response_model=CreateJobResponse)
async def create_job_from_nodes(
    request: CreateJobFromNodesRequest,
    background_tasks: BackgroundTasks,
    repository: GeospatialRepositoryPort = Depends(get_geospatial_repository),
    orchestrator: OptimizationOrchestrator = Depends(get_orchestrator),
) -> dict:
    """The real, Pydantic-validated version of Phase 6's temporary
    main.py bridge -- bridges the Setup screen's city + CSV-upload flow to
    the orchestrator. `request.nodes[0]` is treated as the depot, per this
    project's existing node_ids[0]="depot" convention."""
    nodes = [
        Node(id=n.id, coordinates=GeographicCoordinates(lat=n.lat, lon=n.lon), demand=n.demand)
        for n in request.nodes
    ]
    accident_edge = (
        (request.accident_edge.from_node_id, request.accident_edge.to_node_id)
        if request.accident_edge
        else None
    )
    try:
        distance_matrix, base_time_matrix = repository.build_matrices(
            request.city_id, nodes, accident_edge=accident_edge
        )
    except UnknownCityError as exc:
        raise HTTPException(status_code=404, detail=f"unknown city_id: {request.city_id!r}") from exc

    rng = np.random.default_rng(request.seed)
    time_matrix = inject_stochastic_delay(base_time_matrix, rng, hour_of_day=request.hour_of_day)

    job_id = str(uuid.uuid4())
    job_payload = {
        "time_matrix": time_matrix,
        "distance_matrix": distance_matrix,
        "node_ids": [n.id for n in nodes],
        "demands": [n.demand for n in nodes],
        "vehicle_capacity": request.vehicle_capacity,
        "num_vehicles": request.num_vehicles,
        "depot_index": request.depot_index,
    }
    if request.num_particles is not None:
        job_payload["num_particles"] = request.num_particles
    if request.max_iterations is not None:
        job_payload["max_iterations"] = request.max_iterations
    if request.accident_edge is not None:
        _accident_edges[job_id] = {
            "from_node_id": request.accident_edge.from_node_id,
            "to_node_id": request.accident_edge.to_node_id,
        }

    background_tasks.add_task(
        orchestrator.run_comparison, job_id, job_payload, request.seed, request.time_budget_s
    )
    return {"job_id": job_id}


@router.get("/jobs/{job_id}/stream")
async def stream_job(
    job_id: str, orchestrator: OptimizationOrchestrator = Depends(get_orchestrator)
) -> StreamingResponse:
    return StreamingResponse(
        convergence_event_stream(job_id, orchestrator), media_type="text/event-stream"
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str, orchestrator: OptimizationOrchestrator = Depends(get_orchestrator)
) -> dict:
    result = orchestrator.job_results.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown job_id: {job_id!r}")
    if result["status"] != "done":
        return {"status": result["status"], "detail": result.get("detail")}

    ortools_routes = result["ortools"]["routes"]
    qpso_routes = result["qpso"]["routes"]

    def _to_dicts(routes):
        return [dataclasses.asdict(r) for r in routes]

    ortools_payload = algorithm_result_payload(ortools_routes, result["ortools"]["meta"])
    qpso_payload = algorithm_result_payload(qpso_routes, result["qpso"]["meta"])
    ortools_payload["routes"] = _to_dicts(ortools_routes)
    qpso_payload["routes"] = _to_dicts(qpso_routes)

    return {
        "status": "done",
        "ortools": ortools_payload,
        "qpso": qpso_payload,
        "green_impact": compute_green_impact(ortools_routes, qpso_routes),
        "accident_edge": _accident_edges.get(job_id),
    }
