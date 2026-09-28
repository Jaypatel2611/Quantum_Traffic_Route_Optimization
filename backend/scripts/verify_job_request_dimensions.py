"""Standalone check for CreateJobRequest's dimension validation -- the bug
this guards against: a ragged time_matrix/distance_matrix (rows of unequal
length) or a demands list that doesn't match node_ids used to reach
np.array(..., dtype=float) in optimize_router.create_job unguarded, raising
an unhandled ValueError (500) instead of a clean 422."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.presentation.schemas.optimize_request import CreateJobRequest

BASE = dict(
    node_ids=["depot", "n1", "n2"],
    demands=[0.0, 5.0, 5.0],
    time_matrix=[[0, 1, 2], [1, 0, 3], [2, 3, 0]],
    distance_matrix=[[0, 1, 2], [1, 0, 3], [2, 3, 0]],
    vehicle_capacity=10.0,
    num_vehicles=1,
    seed=1,
    time_budget_s=5.0,
)

if __name__ == "__main__":
    CreateJobRequest(**BASE)  # valid payload must still pass
    print("valid payload: OK")

    for name, override in [
        ("ragged time_matrix row", {"time_matrix": [[0, 1, 2], [1, 0], [2, 3, 0]]}),
        ("distance_matrix too few rows", {"distance_matrix": [[0, 1], [1, 0]]}),
        ("demands length mismatch", {"demands": [0.0, 5.0]}),
        ("depot_index out of range", {"depot_index": 9}),
    ]:
        payload = {**BASE, **override}
        try:
            CreateJobRequest(**payload)
        except ValidationError:
            print(f"{name}: rejected OK")
        else:
            raise AssertionError(f"{name}: should have been rejected by validation")

    print("all checks passed")
