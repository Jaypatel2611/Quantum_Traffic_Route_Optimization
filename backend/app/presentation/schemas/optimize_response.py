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


class AccidentEdgeResponse(BaseModel):
    from_node_id: int
    to_node_id: int


class CreateJobResponse(BaseModel):
    job_id: str


class RouteResponse(BaseModel):
    vehicle_id: str
    node_sequence: list[str]
    total_distance_m: float
    total_time_s: float


class AlgorithmResultResponse(BaseModel):
    routes: list[RouteResponse]
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
    accident_edge: AccidentEdgeResponse | None = None
