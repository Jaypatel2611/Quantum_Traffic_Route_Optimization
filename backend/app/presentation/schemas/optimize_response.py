from pydantic import BaseModel


class CityResponse(BaseModel):
    id: str
    name: str


class EdgeResponse(BaseModel):
    edge_id: str
    from_node_id: int
    to_node_id: int
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    travel_time_s: float  # normal crossing time; an accident adds (multiplier - 1) x this


class AccidentEdgeResponse(BaseModel):
    from_node_id: int
    to_node_id: int


class CreateJobResponse(BaseModel):
    job_id: str


class StopResponse(BaseModel):
    """One visit in a route: the leg that reached it and the running totals."""
    node_id: str
    leg_distance_m: float
    leg_time_s: float
    cumulative_distance_m: float
    cumulative_time_s: float


class RouteResponse(BaseModel):
    vehicle_id: str
    node_sequence: list[str]
    total_distance_m: float
    total_time_s: float
    stops: list[StopResponse] | None = None  # one per node_sequence entry; absent for raw-matrix jobs
    geometry: list[list[float]] | None = None  # road-following [lat, lon] polyline
    # Legs whose road path differs from the no-accident path -- what the
    # accidents forced onto a detour. Empty/absent when no accidents.
    rerouted_geometry: list[list[list[float]]] | None = None


class AccidentImpactResponse(BaseModel):
    from_node_id: int
    to_node_id: int
    status: str  # not_on_route | rerouted | driven_through
    added_time_s: float


class RouteChangesResponse(BaseModel):
    changed: bool
    baseline_sequences: list[list[str]]
    baseline_time_under_accidents_s: float
    actual_time_s: float
    saved_time_s: float


class AlgorithmResultResponse(BaseModel):
    routes: list[RouteResponse]
    route_changes: RouteChangesResponse | None = None
    accident_impacts: list[AccidentImpactResponse] = []
    meta: dict
    total_co2_kg: float
    total_time_s: float


class GreenImpactResponse(BaseModel):
    co2_saved_kg: float
    co2_reduction_percent: float
    fuel_saved_liters: float
    time_saved_s: float
    emission_factor_source: str


class JobResultResponse(BaseModel):
    status: str
    detail: str | None = None
    ortools: AlgorithmResultResponse | None = None
    qpso: AlgorithmResultResponse | None = None
    green_impact: GreenImpactResponse | None = None
    accident_edges: list[AccidentEdgeResponse] = []
    # none (no accidents) | pending (baseline still solving) | ready | unavailable (baseline failed)
    route_changes_status: str = "none"
