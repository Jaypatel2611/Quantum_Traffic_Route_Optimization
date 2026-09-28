from pydantic import BaseModel, ConfigDict, Field, model_validator


class ForbidExtraModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodeSchema(ForbidExtraModel):
    id: str
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    demand: float = Field(default=0.0, ge=0.0)


class AccidentEdgeSchema(ForbidExtraModel):
    """A pair of graph node ids from GET /cities/{city_id}/edges -- Flow C's
    accident injection, order-independent (the underlying repository keys
    it by frozenset)."""
    from_node_id: int
    to_node_id: int


class CreateJobRequest(ForbidExtraModel):
    """Real, Pydantic-validated version of Phase 5's raw-matrix /jobs
    contract -- for a caller that already has a pre-built distance/time
    matrix (a verification script, not the Setup screen's city/CSV flow,
    which goes through CreateJobFromNodesRequest below and never builds a
    matrix client-side)."""
    time_matrix: list[list[float]] = Field(min_length=2, max_length=2000)
    distance_matrix: list[list[float]] = Field(min_length=2, max_length=2000)
    node_ids: list[str] = Field(min_length=2, max_length=2000)
    demands: list[float]
    vehicle_capacity: float = Field(gt=0)
    num_vehicles: int = Field(gt=0, le=50)
    seed: int
    time_budget_s: float = Field(gt=0, le=120)
    depot_index: int = 0
    num_particles: int | None = Field(default=None, gt=0, le=200)
    max_iterations: int | None = Field(default=None, gt=0, le=5000)

    @model_validator(mode="after")
    def _dimensions_consistent(self) -> "CreateJobRequest":
        # Rows of unequal length (well-formed per-field, but ragged as a
        # whole) pass the Field(min_length/max_length) checks above and
        # reach np.array(..., dtype=float) in optimize_router.create_job
        # unguarded -- numpy raises ValueError on an inhomogeneous shape,
        # which FastAPI has no handler for, so it surfaces as an unhandled
        # 500 instead of the 422 this endpoint's docstring promises.
        n = len(self.node_ids)
        if not 0 <= self.depot_index < n:
            raise ValueError("depot_index out of range for node_ids")
        if len(self.demands) != n:
            raise ValueError(f"demands length {len(self.demands)} must equal node_ids length {n}")
        for name, matrix in (("time_matrix", self.time_matrix), ("distance_matrix", self.distance_matrix)):
            if len(matrix) != n or any(len(row) != n for row in matrix):
                raise ValueError(f"{name} must be a square {n}x{n} matrix matching node_ids")
        return self


class CreateJobFromNodesRequest(ForbidExtraModel):
    city_id: str
    nodes: list[NodeSchema] = Field(min_length=2, max_length=2000)
    vehicle_capacity: float = Field(gt=0)
    num_vehicles: int = Field(gt=0, le=50)
    seed: int
    time_budget_s: float = Field(gt=0, le=120)
    depot_index: int = 0
    hour_of_day: float = 8.0
    num_particles: int | None = Field(default=None, gt=0, le=200)
    max_iterations: int | None = Field(default=None, gt=0, le=5000)
    accident_edge: AccidentEdgeSchema | None = None

    @model_validator(mode="after")
    def _depot_index_in_range(self) -> "CreateJobFromNodesRequest":
        if not 0 <= self.depot_index < len(self.nodes):
            raise ValueError("depot_index out of range for nodes")
        return self
