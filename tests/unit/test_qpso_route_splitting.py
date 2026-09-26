import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import split_into_routes, capacity_penalty


def test_splits_into_equal_ish_contiguous_chunks():
    permutation = np.array([2, 0, 3, 1, 4])  # 5 customers, in tour order
    routes = split_into_routes(permutation, num_vehicles=2)
    assert len(routes) == 2
    assert sum(len(r) for r in routes) == 5
    # contiguous: route 0 is a prefix of the tour, route 1 the remainder
    assert routes[0] == [2, 0, 3]
    assert routes[1] == [1, 4]


def test_no_penalty_when_under_capacity():
    routes = [[0, 1], [2, 3]]
    demands = [10.0, 20.0, 15.0, 25.0]  # customer-index-aligned (depot excluded)
    assert capacity_penalty(routes, demands, vehicle_capacity=100.0, lam=50.0) == 0.0


def test_penalty_scales_with_squared_violation():
    routes = [[0, 1]]  # load = 10 + 20 = 30
    demands = [10.0, 20.0]
    # violation = 30 - 25 = 5; penalty = lam * 5^2
    assert capacity_penalty(routes, demands, vehicle_capacity=25.0, lam=2.0) == 2.0 * 5.0**2
