import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import split_into_routes, capacity_penalty

# Two well-separated clusters of 3 customers each (matrix idx 0 = depot,
# customers 0-2 = cluster A at idx 1-3, customers 3-5 = cluster B at idx
# 4-6). Within a cluster (and depot<->A) distance is 1; crossing between
# clusters (or depot<->B) is 50 -- built to make a cross-cluster route
# obviously, measurably worse than two same-cluster routes.
_NEAR, _FAR = 1.0, 50.0


def _clustered_time_matrix() -> np.ndarray:
    m = np.full((7, 7), _FAR)
    np.fill_diagonal(m, 0.0)
    cluster_a = [0, 1, 2, 3]  # depot + customers 0,1,2 (matrix idx 1,2,3)
    cluster_b = [0, 4, 5, 6]  # depot + customers 3,4,5 (matrix idx 4,5,6)
    for cluster in (cluster_a, cluster_b):
        for i in cluster:
            for j in cluster:
                m[i][j] = _NEAR
    np.fill_diagonal(m, 0.0)
    return m


def test_groups_geographically_close_customers_even_with_unequal_route_sizes():
    """The old fixed-size equal-chunk split would force chunks of size 2
    with num_vehicles=3, splitting cluster A (3 customers) across two
    routes and pairing one of its customers with a cluster-B customer --
    the exact failure mode the bigger demo-scenario verification found.
    The geography-aware split must instead group each 3-customer cluster
    into its own route (only 2 of 3 available vehicles used) because that
    is strictly cheaper."""
    time_matrix = _clustered_time_matrix()
    permutation = np.array([0, 1, 2, 3, 4, 5])  # already cluster-ordered tour

    routes = split_into_routes(permutation, num_vehicles=3, time_matrix=time_matrix, depot_index=0)

    non_empty = [r for r in routes if r]
    assert len(non_empty) == 2
    assert sorted(non_empty[0]) == [0, 1, 2] or sorted(non_empty[0]) == [3, 4, 5]
    assert {c for r in routes for c in r} == {0, 1, 2, 3, 4, 5}


def test_covers_every_customer_exactly_once_regardless_of_vehicle_count():
    time_matrix = _clustered_time_matrix()
    permutation = np.array([2, 0, 4, 1, 5, 3])  # any tour order

    routes = split_into_routes(permutation, num_vehicles=4, time_matrix=time_matrix, depot_index=0)

    assert len(routes) == 4
    all_customers = [c for r in routes for c in r]
    assert sorted(all_customers) == [0, 1, 2, 3, 4, 5]


def test_single_vehicle_puts_everyone_on_one_route():
    time_matrix = _clustered_time_matrix()
    permutation = np.array([0, 1, 2, 3, 4, 5])

    routes = split_into_routes(permutation, num_vehicles=1, time_matrix=time_matrix, depot_index=0)

    assert routes == [[0, 1, 2, 3, 4, 5]]


def test_no_penalty_when_under_capacity():
    routes = [[0, 1], [2, 3]]
    demands = [10.0, 20.0, 15.0, 25.0]  # customer-index-aligned (depot excluded)
    assert capacity_penalty(routes, demands, vehicle_capacity=100.0, lam=50.0) == 0.0


def test_penalty_scales_with_squared_violation():
    routes = [[0, 1]]  # load = 10 + 20 = 30
    demands = [10.0, 20.0]
    # violation = 30 - 25 = 5; penalty = lam * 5^2
    assert capacity_penalty(routes, demands, vehicle_capacity=25.0, lam=2.0) == 2.0 * 5.0**2
