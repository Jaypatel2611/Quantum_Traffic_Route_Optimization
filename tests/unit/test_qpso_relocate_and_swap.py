import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import relocate_and_swap_polish

# Same clustered layout as test_qpso_route_splitting.py: customers 0,1,2 near
# each other and the depot; customers 3,4,5 likewise, but far from cluster A.
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


def test_relocates_a_misassigned_customer_into_its_own_cluster():
    """The split/PSO stage got this wrong: customer 2 (cluster A) ended up
    on cluster B's vehicle and vice versa for customer 3. Neither the DP
    split nor two-opt can fix a cross-route assignment -- only this pass
    can, and it must, since fixing it is strictly cheaper."""
    time_matrix = _clustered_time_matrix()
    demands = [10.0] * 6
    bad_routes = [[0, 1, 3], [2, 4, 5]]

    polished = relocate_and_swap_polish(
        bad_routes, time_matrix, demands, vehicle_capacity=100.0, depot_index=0
    )

    all_customers = sorted(c for r in polished for c in r)
    assert all_customers == [0, 1, 2, 3, 4, 5]
    clusters = [frozenset(r) for r in polished if r]
    assert frozenset({0, 1, 2}) in clusters
    assert frozenset({3, 4, 5}) in clusters


def test_never_violates_capacity_to_make_a_move():
    """Every starting route is already exactly at capacity (20 load, 2
    customers x 10 demand each); the full-clustering fix would need a
    3-customer route (30 load), which the tight capacity forbids. The
    polish must never accept a move that pushes any route over capacity,
    even when doing so would otherwise be cheaper."""
    time_matrix = _clustered_time_matrix()
    demands = [10.0] * 6
    routes_at_capacity = [[0, 1], [2, 3], [4, 5]]

    polished = relocate_and_swap_polish(
        routes_at_capacity, time_matrix, demands, vehicle_capacity=20.0, depot_index=0
    )

    assert sorted(c for r in polished for c in r) == [0, 1, 2, 3, 4, 5]
    for route in polished:
        assert sum(demands[c] for c in route) <= 20.0


def test_already_optimal_routes_are_left_alone():
    time_matrix = _clustered_time_matrix()
    demands = [10.0] * 6
    good_routes = [[0, 1, 2], [3, 4, 5]]

    polished = relocate_and_swap_polish(
        good_routes, time_matrix, demands, vehicle_capacity=100.0, depot_index=0
    )

    clusters = [frozenset(r) for r in polished if r]
    assert frozenset({0, 1, 2}) in clusters
    assert frozenset({3, 4, 5}) in clusters


def test_polish_never_duplicates_or_drops_a_customer():
    """Regression: after a successful swap the inner loops kept using the
    pre-swap customer ids, so a later "swap" could copy one customer into a
    route twice and drop another -- which looks cheaper, so it was accepted.
    Any polished solution must still visit every customer exactly once."""
    n = 8
    for seed in range(300):
        rng = np.random.default_rng(seed)
        matrix = rng.uniform(1.0, 60.0, size=(n + 1, n + 1))  # asymmetric, like real one-way roads
        np.fill_diagonal(matrix, 0.0)
        demands = list(rng.uniform(5.0, 30.0, size=n))
        routes = [[0, 1, 2], [3, 4], [5, 6, 7]]
        polished = relocate_and_swap_polish(routes, matrix, demands, vehicle_capacity=80.0)
        assert sorted(c for r in polished for c in r) == list(range(n)), f"seed {seed}: {polished}"
