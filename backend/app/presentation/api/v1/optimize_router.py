import dataclasses
import uuid

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.application.services.green_impact_calculator import algorithm_result_payload, compute_green_impact
from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.application.services.route_changes import compute_route_changes
from app.domain.entities.node import Node
from app.domain.exceptions import UnknownCityError
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.presentation.api.v1.dependencies import get_geospatial_repository, get_orchestrator
from app.presentation.api.v1.job_context import JobContext, add_geometry, add_stops, get_context, remember
from app.presentation.schemas.optimize_request import CreateJobFromNodesRequest, CreateJobRequest
from app.presentation.schemas.optimize_response import CreateJobResponse, JobResultResponse
from app.presentation.sse.convergence_stream import convergence_event_stream

router = APIRouter()

def _job_payload(request, *, time_matrix, distance_matrix, node_ids, demands) -> dict:
    """The solver payload both job endpoints build; optional QPSO knobs only when set."""
    payload = {
        "time_matrix": time_matrix,
        "distance_matrix": distance_matrix,
        "node_ids": node_ids,
        "demands": demands,
        "vehicle_capacity": request.vehicle_capacity,
        "num_vehicles": request.num_vehicles,
        "depot_index": request.depot_index,
    }
    if request.num_particles is not None:
        payload["num_particles"] = request.num_particles
    if request.max_iterations is not None:
        payload["max_iterations"] = request.max_iterations
    return payload


@router.post("/jobs", response_model=CreateJobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    orchestrator: OptimizationOrchestrator = Depends(get_orchestrator),
) -> dict:
    """The real, Pydantic-validated version of Phase 5's raw-matrix bridge
    (main.py's original /jobs) -- same contract, now rejecting malformed
    matrices/counts at the request boundary instead of failing deep inside
    the solver or the orchestrator."""
    job_id = str(uuid.uuid4())
    job_payload = _job_payload(
        request,
        time_matrix=np.array(request.time_matrix, dtype=float),
        distance_matrix=np.array(request.distance_matrix, dtype=float),
        node_ids=request.node_ids,
        demands=request.demands,
    )

    remember(job_id, JobContext(
        node_ids=request.node_ids,
        distance_matrix=job_payload["distance_matrix"],
        time_matrix=job_payload["time_matrix"],
        accident_edges=[],
    ))
    background_tasks.add_task(
        orchestrator.run_comparison, job_id, job_payload, request.seed, request.time_budget_s
    )
    return {"job_id": job_id}


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
    accident_edges = [(a.from_node_id, a.to_node_id) for a in request.accident_edges]
    try:
        distance_matrix, base_time_matrix = repository.build_matrices(
            request.city_id, nodes, accident_edges=accident_edges
        )
    except UnknownCityError as exc:
        raise HTTPException(status_code=404, detail=f"unknown city_id: {request.city_id!r}") from exc

    rng = np.random.default_rng(request.seed)
    time_matrix = inject_stochastic_delay(base_time_matrix, rng, hour_of_day=request.hour_of_day)

    job_id = str(uuid.uuid4())
    job_payload = _job_payload(
        request,
        time_matrix=time_matrix,
        distance_matrix=distance_matrix,
        node_ids=[n.id for n in nodes],
        demands=[n.demand for n in nodes],
    )

    baseline_payload = None
    if accident_edges:
        # Same seed => the same random delay factors, so only the accidents differ.
        free_distance, free_base_time = repository.build_matrices(request.city_id, nodes)
        free_time = inject_stochastic_delay(
            free_base_time, np.random.default_rng(request.seed), hour_of_day=request.hour_of_day
        )
        baseline_payload = {**job_payload, "distance_matrix": free_distance, "time_matrix": free_time}

    remember(job_id, JobContext(
        node_ids=[n.id for n in nodes],
        distance_matrix=distance_matrix,
        time_matrix=time_matrix,
        accident_edges=accident_edges,
        city_id=request.city_id,
        nodes=nodes,
    ))

    background_tasks.add_task(
        orchestrator.run_comparison, job_id, job_payload, request.seed, request.time_budget_s, baseline_payload
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
    job_id: str,
    orchestrator: OptimizationOrchestrator = Depends(get_orchestrator),
    repository: GeospatialRepositoryPort = Depends(get_geospatial_repository),
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

    context = get_context(job_id)
    if context is not None:
        both = ortools_payload["routes"] + qpso_payload["routes"]
        add_stops(both, context)
        if context.city_id is not None:
            add_geometry(both, context, repository)
            if context.accident_edges:
                for payload in (ortools_payload, qpso_payload):
                    payload["accident_impacts"] = repository.accident_impacts(
                        context.city_id,
                        context.nodes,
                        [r["node_sequence"] for r in payload["routes"]],
                        context.accident_edges,
                    )

    baseline = result.get("baseline")
    if context is None or not context.accident_edges or baseline is None:
        route_changes_status = "none"
    elif baseline == "pending":
        route_changes_status = "pending"
    elif baseline == "failed":
        route_changes_status = "unavailable"
    else:
        route_changes_status = "ready"
        for payload, solver, actual_routes in (
            (ortools_payload, "ortools", ortools_routes), (qpso_payload, "qpso", qpso_routes),
        ):
            payload["route_changes"] = compute_route_changes(
                baseline[solver]["routes"], actual_routes, context.node_ids, context.time_matrix
            )

    return {
        "status": "done",
        "ortools": ortools_payload,
        "qpso": qpso_payload,
        "green_impact": compute_green_impact(ortools_routes, qpso_routes),
        "route_changes_status": route_changes_status,
        "accident_edges": [
            {"from_node_id": a, "to_node_id": b} for a, b in (context.accident_edges if context else [])
        ],
    }
