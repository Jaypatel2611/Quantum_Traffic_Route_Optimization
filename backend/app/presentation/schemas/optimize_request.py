from pydantic import BaseModel, Field


class NodeSchema(BaseModel):
    id: str
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    demand: float = Field(default=0.0, ge=0.0)


class AccidentEdgeSchema(BaseModel):
    """A pair of graph node ids from GET /cities/{city_id}/edges -- Flow C's
    accident injection, order-independent (the underlying repository keys
    it by frozenset)."""
    from_node_id: int
    to_node_id: int


class CreateJobFromNodesRequest(BaseModel):
    city_id: str
    nodes: list[NodeSchema] = Field(min_length=2)
    vehicle_capacity: float = Field(gt=0)
    num_vehicles: int = Field(gt=0)
    seed: int
    time_budget_s: float = Field(gt=0)
    depot_index: int = 0
    hour_of_day: float = 8.0
    num_particles: int | None = Field(default=None, gt=0)
    max_iterations: int | None = Field(default=None, gt=0)
    accident_edge: AccidentEdgeSchema | None = None
