import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import two_opt_route

# depot(0) -> A(1) -> B(2) -> C(3) -> D(4) -> depot is a cheap 5-edge loop
# (cost 1 each); every other pair costs 10. Any route order other than the
# loop's own sequence (or its reverse) must cross expensive edges.
_CHEAP_EDGES = {(0, 1): 1, (1, 2): 1, (2, 3): 1, (3, 4): 1, (4, 0): 1}


def _matrix() -> np.ndarray:
    m = np.full((5, 5), 10.0)
    np.fill_diagonal(m, 0.0)
    for (a, b), cost in _CHEAP_EDGES.items():
        m[a][b] = cost
        m[b][a] = cost
    return m


def _route_time(route: list[int], time_matrix, depot_index=0) -> float:
    stops = [depot_index] + [c + 1 for c in route] + [depot_index]
    return sum(time_matrix[a][b] for a, b in zip(stops, stops[1:]))


def test_untangles_a_crossed_route_into_the_cheap_loop_order():
    time_matrix = _matrix()
    bad_order = [2, 0, 3, 1]  # C, A, D, B -- crosses the cheap loop badly
    assert _route_time(bad_order, time_matrix) == 50.0

    polished = two_opt_route(bad_order, time_matrix, depot_index=0)

    assert _route_time(polished, time_matrix) == 5.0
    assert sorted(polished) == sorted(bad_order)  # same customers, only reordered


def test_never_makes_an_already_optimal_route_worse():
    time_matrix = _matrix()
    good_order = [0, 1, 2, 3]  # A, B, C, D -- already the cheap loop order
    polished = two_opt_route(good_order, time_matrix, depot_index=0)
    assert _route_time(polished, time_matrix) == 5.0


def test_leaves_short_routes_untouched():
    time_matrix = _matrix()
    assert two_opt_route([], time_matrix) == []
    assert two_opt_route([0], time_matrix) == [0]
    assert two_opt_route([0, 1], time_matrix) == [0, 1]
