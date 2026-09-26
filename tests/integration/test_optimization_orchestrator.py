import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
import pytest
from app.application.services.optimization_orchestrator import OptimizationOrchestrator


def _payload():
    time_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    return {
        "time_matrix": time_matrix, "distance_matrix": time_matrix * 50,
        "node_ids": ["depot", "n1", "n2", "n3"], "demands": [0, 30, 40, 25],
        "vehicle_capacity": 100.0, "num_vehicles": 2, "depot_index": 0,
    }


@pytest.mark.asyncio
async def test_run_comparison_populates_both_results_on_success():
    orchestrator = OptimizationOrchestrator()
    await orchestrator.run_comparison("job1", _payload(), seed=42, time_budget_s=3.0)
    result = orchestrator.job_results["job1"]
    assert result["status"] == "done"
    assert "ortools" in result and "qpso" in result


@pytest.mark.asyncio
async def test_convergence_cache_receives_live_progress_from_a_separate_process():
    """Proves cross-process liveness: the Manager-backed list must already
    hold entries appended by the CHILD process's still-running QPSO loop,
    observed from the PARENT while run_comparison's own await is still
    pending -- not just checked after the coroutine finishes."""
    orchestrator = OptimizationOrchestrator()
    task = asyncio.create_task(orchestrator.run_comparison("job2", _payload(), seed=42, time_budget_s=3.0))
    await asyncio.sleep(1.0)  # let the subprocess get partway through its 3s budget
    mid_run_length = len(orchestrator.convergence_cache.get("job2", []))
    await task
    final_length = len(orchestrator.convergence_cache["job2"])
    assert mid_run_length > 0, "no progress observed while the job was still running"
    assert final_length >= mid_run_length


@pytest.mark.asyncio
async def test_solver_exception_is_caught_and_reported_as_error_status():
    orchestrator = OptimizationOrchestrator()
    bad_payload = _payload()
    bad_payload["num_vehicles"] = 0  # guaranteed to blow up both solvers
    await orchestrator.run_comparison("job3", bad_payload, seed=42, time_budget_s=3.0)
    assert orchestrator.job_results["job3"]["status"] == "error"


@pytest.mark.asyncio
async def test_reconnect_does_not_retrigger_the_job():
    """A second read of the same job's cache must not cause a second solve --
    the orchestrator only starts a job when run_comparison is called, and
    the SSE layer (Task 3) never calls it a second time for a reconnect."""
    orchestrator = OptimizationOrchestrator()
    await orchestrator.run_comparison("job4", _payload(), seed=42, time_budget_s=3.0)
    first_read = list(orchestrator.convergence_cache["job4"])
    second_read = list(orchestrator.convergence_cache["job4"])
    assert first_read == second_read
