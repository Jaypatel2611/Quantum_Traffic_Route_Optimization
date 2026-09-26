import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
import pytest
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp


def _small_instance():
    # depot + 3 customers, small enough to solve instantly
    time_matrix = np.array(
        [
            [0, 10, 15, 20],
            [10, 0, 12, 18],
            [15, 12, 0, 8],
            [20, 18, 8, 0],
        ],
        dtype=float,
    )
    distance_matrix = time_matrix * 50  # arbitrary meters-per-second-ish scaling for the test
    node_ids = ["depot", "n1", "n2", "n3"]
    demands = [0, 30, 40, 25]
    return time_matrix, distance_matrix, node_ids, demands


def test_all_customers_visited_exactly_once():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, meta = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    visited = [node for route in routes for node in route.node_sequence if node != "depot"]
    assert sorted(visited) == ["n1", "n2", "n3"]


def test_every_route_starts_and_ends_at_depot():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, _ = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    for route in routes:
        assert route.node_sequence[0] == "depot"
        assert route.node_sequence[-1] == "depot"


def test_capacity_constraint_is_respected():
    # total demand (95) exceeds a single vehicle's capacity (70), forcing a real
    # split across the 2 available vehicles -- but every pairwise combination
    # (55, 65, 70) still fits, so this is feasible, not infeasible-by-construction.
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, _ = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=70.0, num_vehicles=2, time_limit_s=5.0,
    )
    demand_by_id = dict(zip(node_ids, demands))
    assert len(routes) == 2
    for route in routes:
        route_demand = sum(demand_by_id[n] for n in route.node_sequence if n != "depot")
        assert route_demand <= 70.0


def test_known_seed_limitation_is_reported_not_silenced():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    _, meta = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    assert meta["seed_configurable"] is False
    assert meta["first_solution_strategy"] == "PATH_CHEAPEST_ARC"
    assert meta["local_search_metaheuristic"] == "GUIDED_LOCAL_SEARCH"


def test_infeasible_capacity_raises_clear_error():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    with pytest.raises(RuntimeError, match="feasible"):
        solve_cvrp(
            time_matrix, distance_matrix, node_ids, demands,
            vehicle_capacity=10.0, num_vehicles=1, time_limit_s=2.0,
        )
