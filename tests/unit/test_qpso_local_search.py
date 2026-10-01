import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_local_search import (
    improve_routes,
    nearest_neighbor_tour,
    solution_cost,
    tour_to_position,
)
from app.infrastructure.algorithms.qpso_solver import rov_map, run_qpso


def _instance(n, seed):
    rng = np.random.default_rng(seed)
    matrix = rng.uniform(5.0, 80.0, size=(n + 1, n + 1))  # asymmetric, like one-way roads
    np.fill_diagonal(matrix, 0.0)
    demands = list(rng.uniform(5.0, 25.0, size=n))
    return matrix, demands


def _visited_once(routes, n):
    return sorted(c for r in routes for c in r) == list(range(n))


def _load(route, demands):
    return sum(demands[c] for c in route)


def test_warm_start_tour_visits_everyone_and_round_trips_through_the_swarms_encoding():
    matrix, _ = _instance(12, 1)
    tour = nearest_neighbor_tour(matrix, 12)
    assert sorted(tour) == list(range(12))
    assert list(rov_map(tour_to_position(tour, 12))) == tour


def test_improve_routes_never_duplicates_or_drops_a_customer_and_never_gets_worse():
    n = 18
    for seed in range(15):
        matrix, demands = _instance(n, seed)
        rng = np.random.default_rng(seed)
        order = list(rng.permutation(n))
        start = [order[0:6], order[6:12], order[12:18]]
        cap = 90.0
        before = solution_cost(start, matrix, demands, cap, 0)
        result = improve_routes(start, matrix, demands, cap, 0, deadline=time.monotonic() + 0.4, rng=rng)
        assert _visited_once(result, n), f"seed {seed}: {result}"
        assert solution_cost(result, matrix, demands, cap, 0) <= before + 1e-9


def test_improve_routes_repairs_an_over_capacity_start_when_a_feasible_split_exists():
    n = 12
    matrix, demands = _instance(n, 7)
    cap = sum(demands) / 3 * 1.4
    start = [list(range(n)), [], []]  # everything on one truck: badly over capacity
    result = improve_routes(start, matrix, demands, cap, 0, deadline=time.monotonic() + 1.0, rng=np.random.default_rng(0))
    assert _visited_once(result, n)
    assert all(_load(r, demands) <= cap + 1e-9 for r in result)


def test_improve_routes_respects_its_deadline():
    matrix, demands = _instance(40, 3)
    start = [list(range(0, 20)), list(range(20, 40))]
    t0 = time.monotonic()
    improve_routes(start, matrix, demands, 1e9, 0, deadline=t0 + 0.5, rng=np.random.default_rng(0))
    assert time.monotonic() - t0 < 1.5


def test_run_qpso_end_to_end_is_valid_feasible_and_within_its_budget():
    n = 25
    matrix, demands = _instance(n, 11)
    cap = sum(demands) / 4 * 1.3
    t0 = time.monotonic()
    routes, _, meta = run_qpso(
        matrix, matrix, demands, vehicle_capacity=cap, num_vehicles=4, depot_index=0,
        num_particles=20, max_iterations=100_000, time_budget_s=2.0, seed=42,
    )
    assert time.monotonic() - t0 < 3.5  # swarm + local search share ONE budget
    assert _visited_once(routes, n)
    assert all(_load(r, demands) <= cap + 1e-9 for r in routes)
    assert meta["swarm_share"] < 1.0
