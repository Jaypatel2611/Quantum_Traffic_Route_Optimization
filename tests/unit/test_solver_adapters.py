import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.or_tools_baseline import run_ortools_job
from app.infrastructure.algorithms.qpso_solver import run_qpso_job
from app.domain.entities.route import Route


def _payload():
    time_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    distance_matrix = time_matrix * 50
    return {
        "time_matrix": time_matrix,
        "distance_matrix": distance_matrix,
        "node_ids": ["depot", "n1", "n2", "n3"],
        "demands": [0, 30, 40, 25],
        "vehicle_capacity": 100.0,
        "num_vehicles": 2,
        "depot_index": 0,
    }


def test_ortools_adapter_returns_common_shape():
    result = run_ortools_job(_payload(), seed=42, time_budget_s=5.0)
    assert set(result.keys()) == {"routes", "meta"}
    assert all(isinstance(r, Route) for r in result["routes"])


def test_qpso_adapter_returns_common_shape():
    result = run_qpso_job(_payload(), seed=42, time_budget_s=5.0)
    assert set(result.keys()) == {"routes", "meta"}
    assert all(isinstance(r, Route) for r in result["routes"])
    assert "convergence_history" in result["meta"]


def test_qpso_adapter_appends_to_progress_list_live():
    """The whole point of progress_list: it must be populated as the run
    progresses, not just equal to the final convergence_history at the end
    -- this test can't fully prove cross-process liveness (that's Task 2's
    job with a real ProcessPoolExecutor) but does prove the adapter writes
    into whatever list-like object it's given, iteration by iteration."""
    progress = []
    run_qpso_job(_payload(), seed=42, time_budget_s=5.0, progress_list=progress)
    assert len(progress) > 0
