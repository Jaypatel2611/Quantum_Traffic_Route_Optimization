import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import run_qpso


def _small_instance():
    distance_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    time_matrix = distance_matrix / 2
    demands = [30.0, 40.0, 25.0]  # 3 customers, depot excluded
    return distance_matrix, time_matrix, demands


def test_same_seed_reproduces_identical_convergence_history():
    distance_matrix, time_matrix, demands = _small_instance()
    _, _, meta_a = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    _, _, meta_b = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    assert meta_a["convergence_history"] == meta_b["convergence_history"]


def test_gbest_fitness_never_increases_across_iterations():
    distance_matrix, time_matrix, demands = _small_instance()
    _, _, meta = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=30, time_budget_s=5.0, seed=1,
    )
    history = meta["convergence_history"]
    assert all(history[i + 1] <= history[i] + 1e-9 for i in range(len(history) - 1))


def test_wall_clock_time_budget_is_enforced():
    distance_matrix, time_matrix, demands = _small_instance()
    start = time.monotonic()
    _, _, meta = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=1_000_000, time_budget_s=1.0, seed=1,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 3.0  # generous margin over the 1.0s budget
    assert meta["stopped_reason"] == "time_budget"


def test_best_route_visits_every_customer_exactly_once():
    distance_matrix, time_matrix, demands = _small_instance()
    routes, _, _ = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    visited = sorted(c for route in routes for c in route)
    assert visited == [0, 1, 2]


def test_convergence_is_genuine_not_degenerate_on_an_uncorrelated_instance():
    """Regression test for a real bug found via manual verification (not this
    suite): with distance and time perfectly proportional (or a search space
    small enough that the optimum is found immediately), the winning particle
    floors both normalized components to exactly 0 in iteration 0 and stays
    there forever -- which looks identical to a broken fitness signal. This
    instance uses independent, uncorrelated distance/time matrices on a
    bigger customer count, where genuine iterative improvement is actually
    observable if the normalization/convergence machinery works."""
    rng = np.random.default_rng(7)
    n = 12
    size = n + 1
    coords = rng.uniform(0, 1000, size=(size, 2))
    distance_matrix = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    time_matrix = rng.uniform(5, 50, size=(size, size))
    time_matrix = (time_matrix + time_matrix.T) / 2
    np.fill_diagonal(time_matrix, 0)
    demands = list(rng.uniform(5, 20, size=n))

    _, _, meta = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=80.0, num_vehicles=3,
        depot_index=0, num_particles=20, max_iterations=200, time_budget_s=10.0, seed=42,
    )
    history = meta["convergence_history"]
    assert len(set(history)) > 1, "convergence history is flat -- normalization/fitness signal is degenerate"
    assert history[-1] < history[0]
