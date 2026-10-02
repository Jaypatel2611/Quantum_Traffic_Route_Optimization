import dataclasses
from collections import OrderedDict

import numpy as np

from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.domain.entities.node import Node


@dataclasses.dataclass
class JobContext:
    """What /result needs beyond the solvers' own output -- a presentation-layer
    concern, so it lives here rather than in OptimizationOrchestrator's state.
    city_id/nodes are None for raw-matrix /jobs (no road geometry for those)."""
    node_ids: list[str]
    distance_matrix: np.ndarray
    time_matrix: np.ndarray
    accident_edges: list[tuple[int, int]]
    city_id: str | None = None
    nodes: list[Node] | None = None


_MAX_JOB_CONTEXTS = 50  # each holds two NxN matrices; oldest evicted first
_job_contexts: "OrderedDict[str, JobContext]" = OrderedDict()


def remember(job_id: str, context: JobContext) -> None:
    _job_contexts[job_id] = context
    while len(_job_contexts) > _MAX_JOB_CONTEXTS:
        _job_contexts.popitem(last=False)


def get_context(job_id: str) -> JobContext | None:
    return _job_contexts.get(job_id)


def add_stops(routes: list[dict], context: JobContext) -> None:
    """Per-visit leg and cumulative distance/time, from the very matrices the
    solvers optimized over, so the legs sum exactly to each route's totals."""
    index = {node_id: i for i, node_id in enumerate(context.node_ids)}
    for route in routes:
        cumulative_distance = cumulative_time = 0.0
        stops = []
        previous = None
        for node_id in route["node_sequence"]:
            leg_distance = leg_time = 0.0
            if previous is not None:
                leg_distance = float(context.distance_matrix[index[previous]][index[node_id]])
                leg_time = float(context.time_matrix[index[previous]][index[node_id]])
            cumulative_distance += leg_distance
            cumulative_time += leg_time
            stops.append({
                "node_id": node_id,
                "leg_distance_m": leg_distance,
                "leg_time_s": leg_time,
                "cumulative_distance_m": cumulative_distance,
                "cumulative_time_s": cumulative_time,
            })
            previous = node_id
        route["stops"] = stops


def add_geometry(routes: list[dict], context: JobContext, repository: GeospatialRepositoryPort) -> None:
    sequences = [r["node_sequence"] for r in routes]
    legs = repository.route_leg_geometries(
        context.city_id, context.nodes, sequences, accident_edges=context.accident_edges
    )
    free_legs = (
        repository.route_leg_geometries(context.city_id, context.nodes, sequences)
        if context.accident_edges
        else None
    )
    for i, route in enumerate(routes):
        route["geometry"] = [point for leg in legs[i] for point in leg]
        if free_legs is not None:
            route["rerouted_geometry"] = [
                leg for leg, free in zip(legs[i], free_legs[i]) if leg != free
            ]
