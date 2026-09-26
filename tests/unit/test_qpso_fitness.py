import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import evaluate_fitness


def _tiny_instance():
    # depot(0) + 2 customers(1,2)
    distance_matrix = np.array([[0, 10, 20], [10, 0, 15], [20, 15, 0]], dtype=float)
    time_matrix = distance_matrix / 2
    demands = [5.0, 5.0]  # customer-index-aligned (depot excluded)
    return distance_matrix, time_matrix, demands


def test_fitness_is_zero_penalty_when_within_capacity():
    distance_matrix, time_matrix, demands = _tiny_instance()
    routes = [[0, 1]]  # both customers on one vehicle
    score = evaluate_fitness(
        routes, distance_matrix, time_matrix, demands,
        vehicle_capacity=100.0, lam=50.0, depot_index=0,
        w_distance=0.5, w_time=0.5,
        population_distance_range=(0.0, 50.0), population_time_range=(0.0, 25.0),
    )
    assert score.penalty_component == 0.0
    assert score.total >= 0.0


def test_fitness_includes_penalty_when_over_capacity():
    distance_matrix, time_matrix, demands = _tiny_instance()
    routes = [[0, 1]]
    score = evaluate_fitness(
        routes, distance_matrix, time_matrix, demands,
        vehicle_capacity=5.0, lam=10.0, depot_index=0,  # capacity 5 < load 10
        w_distance=0.5, w_time=0.5,
        population_distance_range=(0.0, 50.0), population_time_range=(0.0, 25.0),
    )
    assert score.penalty_component == 10.0 * 5.0**2  # violation = 10 - 5 = 5
    assert score.total > score.distance_component + score.time_component
