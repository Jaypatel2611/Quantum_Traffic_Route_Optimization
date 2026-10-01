import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
import pytest
from app.application.services.route_changes import compute_route_changes
from app.domain.entities.route import Route

NODE_IDS = ["depot", "a", "b"]
# Time under the accidents: depot->a is cheap, depot->b is slow, a<->b moderate.
TIME = np.array([
    [0, 10, 100],
    [10, 0, 30],
    [100, 30, 0],
], dtype=float)


def _route(sequence, time_s):
    return Route(vehicle_id="v0", node_sequence=sequence, total_distance_m=0.0, total_time_s=time_s)


def test_same_stop_order_is_unchanged_and_saves_nothing():
    routes = [_route(["depot", "a", "b", "depot"], 140.0)]
    result = compute_route_changes(routes, routes, NODE_IDS, TIME)
    assert result["changed"] is False
    assert result["saved_time_s"] == 0.0


def test_a_different_order_is_flagged_even_when_it_saves_nothing():
    baseline = [_route(["depot", "b", "a", "depot"], 0.0)]  # solved without accidents
    actual = [_route(["depot", "a", "b", "depot"], 140.0)]  # chosen with them
    result = compute_route_changes(baseline, actual, NODE_IDS, TIME)

    assert result["changed"] is True
    assert result["baseline_sequences"] == [["depot", "b", "a", "depot"]]
    # symmetric costs: the old order is 100 + 30 + 10 = 140 under the accidents, same as the new one
    assert result["baseline_time_under_accidents_s"] == pytest.approx(140.0)
    assert result["actual_time_s"] == 140.0
    assert result["saved_time_s"] == pytest.approx(0.0)


def test_saved_time_is_positive_when_the_new_order_beats_the_old_one_under_the_accidents():
    time = np.array([[0, 10, 50], [10, 0, 5], [200, 5, 0]], dtype=float)  # b->depot now very slow
    baseline = [_route(["depot", "a", "b", "depot"], 0.0)]  # 10 + 5 + 200 = 215 under accidents
    actual = [_route(["depot", "b", "a", "depot"], 65.0)]  # 50 + 5 + 10
    result = compute_route_changes(baseline, actual, NODE_IDS, time)
    assert result["changed"] is True
    assert result["saved_time_s"] == pytest.approx(150.0)


def test_vehicle_assignment_order_does_not_count_as_a_change():
    a = _route(["depot", "a", "depot"], 20.0)
    b = _route(["depot", "b", "depot"], 200.0)
    assert compute_route_changes([a, b], [b, a], NODE_IDS, TIME)["changed"] is False
