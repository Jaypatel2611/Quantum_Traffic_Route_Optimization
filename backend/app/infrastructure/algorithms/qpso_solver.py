import numpy as np

from app.domain.value_objects.fitness_score import FitnessScore


def rov_map(position: np.ndarray) -> np.ndarray:
    """Rank-Order Value mapping (PRD Section 9): sorts the continuous position
    vector and returns the resulting rank order as a discrete node-visit
    permutation. Validity is a structural property of argsort, not something
    the fitness function needs to check."""
    return np.argsort(position)


def split_into_routes(permutation: np.ndarray, num_vehicles: int) -> list[list[int]]:
    """Divides the giant tour into num_vehicles fixed, equal-ish contiguous
    chunks (user-approved encoding, PRD Section 9's particle stays R^N with
    no extra split-point genes)."""
    n = len(permutation)
    base_size, remainder = divmod(n, num_vehicles)
    routes = []
    start = 0
    for vehicle in range(num_vehicles):
        size = base_size + (1 if vehicle < remainder else 0)
        routes.append(permutation[start:start + size].tolist())
        start += size
    return routes


def capacity_penalty(
    routes: list[list[int]], demands: list[float], vehicle_capacity: float, lam: float
) -> float:
    """PRD Section 12's dynamic scaling penalty: an over-capacity route is
    never discarded, just penalized proportional to the squared violation."""
    total = 0.0
    for route in routes:
        load = sum(demands[i] for i in route)
        violation = max(0.0, load - vehicle_capacity)
        total += lam * violation**2
    return total


def _route_distance_and_time(route: list[int], distance_matrix, time_matrix, depot_index: int):
    """One route's round trip: depot -> customers in order -> depot.
    `route` holds customer indices (0-based into the customer list); the
    matrices are depot-inclusive, so shift by +1 to reach matrix indices."""
    stops = [depot_index] + [c + 1 for c in route] + [depot_index]
    dist = sum(distance_matrix[a][b] for a, b in zip(stops, stops[1:]))
    time = sum(time_matrix[a][b] for a, b in zip(stops, stops[1:]))
    return dist, time


def evaluate_fitness(
    routes: list[list[int]],
    distance_matrix,
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    lam: float,
    depot_index: int,
    w_distance: float,
    w_time: float,
    population_distance_range: tuple[float, float],
    population_time_range: tuple[float, float],
) -> FitnessScore:
    """PRD Section 11's multi-objective Min-Max normalization + Section 12's
    dynamic penalty, combined into one scalar fitness."""
    total_distance = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in routes)
    total_time = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in routes)

    dist_min, dist_max = population_distance_range
    time_min, time_max = population_time_range
    dist_norm = 0.0 if dist_max == dist_min else (total_distance - dist_min) / (dist_max - dist_min)
    time_norm = 0.0 if time_max == time_min else (total_time - time_min) / (time_max - time_min)

    penalty = capacity_penalty(routes, demands, vehicle_capacity, lam)
    total = w_distance * dist_norm + w_time * time_norm + penalty
    return FitnessScore(
        total=total,
        distance_component=w_distance * dist_norm,
        time_component=w_time * time_norm,
        penalty_component=penalty,
    )
