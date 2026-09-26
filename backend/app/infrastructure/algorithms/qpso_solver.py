import time

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


def run_qpso(
    distance_matrix,
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    depot_index: int,
    num_particles: int,
    max_iterations: int,
    time_budget_s: float,
    seed: int,
    k: float = 1.75,
    lambda_min: float = 1.0,
    lambda_max: float = 100.0,
    w_distance: float = 0.5,
    w_time: float = 0.5,
):
    """PRD Section 9's QPSO: ROV mapping, local attractor point, mean-best
    position, Monte Carlo position update with a 50/50 sign draw, adaptive
    alpha contraction-expansion schedule. One seeded Generator drives every
    stochastic draw (PRD Section 7) -- never bare numpy.random."""
    rng = np.random.default_rng(seed)
    n = len(demands)  # customer count (depot excluded, PRD Section 9's R^N)

    positions = rng.uniform(-1.0, 1.0, size=(num_particles, n))
    pbest_positions = positions.copy()
    pbest_fitness = [None] * num_particles
    gbest_position = None
    gbest_fitness = None
    convergence_history: list[float] = []
    stagnation_counter = 0
    start = time.monotonic()
    stopped_reason = "max_iterations"

    iteration = 0
    for iteration in range(max_iterations):
        if time.monotonic() - start >= time_budget_s:
            stopped_reason = "time_budget"
            break

        alpha = 1.0 - (1.0 - 0.5) * (iteration / max_iterations) ** k
        lam = lambda_min + (lambda_max - lambda_min) * (iteration / max_iterations) ** k

        all_routes = [split_into_routes(rov_map(p), num_vehicles) for p in positions]
        all_distances = []
        all_times = []
        for routes in all_routes:
            d = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in routes)
            t = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in routes)
            all_distances.append(d)
            all_times.append(t)
        dist_range = (min(all_distances), max(all_distances))
        time_range = (min(all_times), max(all_times))

        fitness_values = [
            evaluate_fitness(
                all_routes[i], distance_matrix, time_matrix, demands, vehicle_capacity,
                lam=lam, depot_index=depot_index, w_distance=w_distance, w_time=w_time,
                population_distance_range=dist_range, population_time_range=time_range,
            )
            for i in range(num_particles)
        ]

        for i, score in enumerate(fitness_values):
            if pbest_fitness[i] is None or score.total < pbest_fitness[i].total:
                pbest_fitness[i] = score
                pbest_positions[i] = positions[i].copy()

        best_idx = min(range(num_particles), key=lambda i: fitness_values[i].total)
        improved = gbest_fitness is None or fitness_values[best_idx].total < gbest_fitness.total * (1 - 0.0001)
        if gbest_fitness is None or fitness_values[best_idx].total < gbest_fitness.total:
            gbest_fitness = fitness_values[best_idx]
            gbest_position = positions[best_idx].copy()
        stagnation_counter = 0 if improved else stagnation_counter + 1
        convergence_history.append(gbest_fitness.total)

        mbest = pbest_positions.mean(axis=0)
        phi = rng.uniform(0.0, 1.0, size=(num_particles, n))
        attractor = phi * pbest_positions + (1 - phi) * gbest_position
        u = rng.uniform(1e-12, 1.0, size=(num_particles, n))  # avoid ln(1/0)
        sign = np.where(rng.random(size=(num_particles, n)) < 0.5, 1.0, -1.0)
        positions = attractor + sign * alpha * np.abs(mbest - positions) * np.log(1.0 / u)

    best_routes = split_into_routes(rov_map(gbest_position), num_vehicles)
    meta = {
        "seed": seed,
        "convergence_history": convergence_history,
        "iterations_run": iteration + 1,
        "stopped_reason": stopped_reason,
    }
    return best_routes, gbest_fitness, meta
