import time

import numpy as np

from app.domain.entities.route import Route
from app.domain.value_objects.fitness_score import FitnessScore
from types import SimpleNamespace

from app.infrastructure.algorithms.copert_model import route_emissions
from app.infrastructure.algorithms.qpso_local_search import (
    improve_routes,
    nearest_neighbor_tour,
    tour_to_position,
)

SWARM_SHARE = 0.4
"""Fraction of the time budget the swarm itself gets; the rest goes to the local
search that polishes its best routes. The total stays inside the one shared
budget OR-Tools also gets, so the comparison remains fair."""


def rov_map(position: np.ndarray) -> np.ndarray:
    """Rank-Order Value mapping (PRD Section 9): sorts the continuous position
    vector and returns the resulting rank order as a discrete node-visit
    permutation. Validity is a structural property of argsort, not something
    the fitness function needs to check."""
    return np.argsort(position)


def split_into_routes(
    permutation: np.ndarray,
    num_vehicles: int,
    time_matrix,
    depot_index: int = 0,
) -> list[list[int]]:
    """Geography-aware split (Prins-style DP over the giant tour, PRD
    Section 9's particle stays R^N with no extra split-point genes -- the
    ROV permutation still fixes the *visiting order*; this only decides
    *where* to cut that fixed order into at most num_vehicles routes,
    minimizing total route time).

    Replaces an earlier fixed-size equal-chunk split: a chunk boundary
    picked by index alone could pair two geographically far-apart
    customers into one vehicle's route purely because of where they landed
    in the permutation. That barely showed at 4-5 customers (found via the
    bigger demo-scenario verification, not a test) but produced routes
    dramatically worse than OR-Tools's at 15-60 customers -- QPSO's own
    fitness had converged, but the *routes* it converged to were bad
    because the split, not the search, was geography-blind.

    Capacity is deliberately NOT enforced here -- that stays
    evaluate_fitness's soft penalty (Section 12), exactly as it was for the
    old equal-chunk split; this function only ever decides where to cut a
    fixed order, never whether a resulting route is feasible."""
    n = len(permutation)
    customers = permutation.astype(int)
    cust_idx = customers + 1  # matrix index: depot occupies row/col 0

    # arc_time[i][j] = round-trip time for the single route visiting
    # customers[i:j] (0 <= i < j <= n): depot -> customers[i] -> ... ->
    # customers[j-1] -> depot. This decomposes additively as A[i] + B[j-1]
    # (depot-to-i and j-to-depot legs, plus the tour's own cumulative
    # sequential travel time between them) -- a fully vectorized O(n)
    # construction instead of an O(n^2) double loop, which mattered in
    # practice: an O(n^2)-per-call, O(K*n^2)-DP split is cheap at 4-5
    # customers but expensive enough at 60 to burn most of a particle's
    # iteration budget, found by checking iterations_run/stopped_reason on
    # the bigger demo scenario after the first (unvectorized) version of
    # this fix quietly turned "more search time" into "less search time".
    depot_to_cust = time_matrix[depot_index, cust_idx]
    cust_to_depot = time_matrix[cust_idx, depot_index]
    prefix = np.concatenate(([0.0], np.cumsum(time_matrix[cust_idx[:-1], cust_idx[1:]]))) if n > 1 else np.zeros(1)
    a = depot_to_cust - prefix
    b = prefix + cust_to_depot

    # dp[j] = min total time to cover customers[:j] with the routes used so
    # far. Because arc_time separates into a[i] + b[j-1], the classic
    # O(n^2) transition dp[k][j] = min_i(dp[k-1][i] + arc_time[i][j])
    # reduces to a running minimum of (dp[k-1][i] + a[i]) -- O(n) per
    # vehicle layer instead of O(n^2), so the whole DP is O(num_vehicles * n).
    inf = float("inf")
    dp = np.full(n + 1, inf)
    dp[0] = 0.0
    parent: list[list[int]] = [[-1] * (n + 1) for _ in range(num_vehicles + 1)]
    dp_at_n = [inf] * (num_vehicles + 1)

    for k in range(1, num_vehicles + 1):
        c = dp[:n] + a
        best_val, best_idx = float(c[0]), 0
        running_min = np.empty(n)
        running_argmin = np.empty(n, dtype=int)
        for i in range(n):
            if c[i] <= best_val:
                best_val, best_idx = float(c[i]), i
            running_min[i] = best_val
            running_argmin[i] = best_idx

        new_dp = np.full(n + 1, inf)
        new_dp[1:] = running_min + b
        for j in range(1, n + 1):
            parent[k][j] = int(running_argmin[j - 1])
        dp_at_n[k] = new_dp[n]
        dp = new_dp

    best_k = min(range(1, num_vehicles + 1), key=lambda k: dp_at_n[k])

    routes: list[list[int]] = []
    j = n
    for k in range(best_k, 0, -1):
        i = parent[k][j]
        routes.append(customers[i:j].tolist())
        j = i
    routes.reverse()
    while len(routes) < num_vehicles:
        routes.append([])
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


def _candidate_key(routes, distance_matrix, time_matrix, demands, vehicle_capacity, depot_index):
    """Rank polished candidates: feasible first, then lowest estimated CO2, then time."""
    overload = sum(max(0.0, sum(demands[c] for c in r) - vehicle_capacity) for r in routes)
    co2 = total_time = 0.0
    for route in routes:
        if not route:
            continue
        d, t = _route_distance_and_time(route, distance_matrix, time_matrix, depot_index)
        co2 += route_emissions(SimpleNamespace(total_distance_m=d, total_time_s=t)).total_kg
        total_time += t
    return (overload > 1e-9, co2, total_time)


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


def reinitialize_stagnant_particles(positions, pbest_fitness, rng, fraction: float = 0.2):
    """PRD Section 15: if Gbest fails to improve for 50 consecutive iterations,
    vaporize and randomly re-initialize the worst-performing fraction of the
    swarm (ranked by personal-best fitness), forcing renewed exploration."""
    num_particles = len(positions)
    num_reinit = max(1, int(num_particles * fraction))
    ranked = sorted(range(num_particles), key=lambda i: pbest_fitness[i].total, reverse=True)
    reinit_indices = sorted(ranked[:num_reinit])
    new_positions = positions.copy()
    for i in reinit_indices:
        new_positions[i] = rng.uniform(-1.0, 1.0, size=positions.shape[1])
    return new_positions, reinit_indices


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
    progress_list=None,
):
    """PRD Section 9's QPSO: ROV mapping, local attractor point, mean-best
    position, Monte Carlo position update with a 50/50 sign draw, adaptive
    alpha contraction-expansion schedule. One seeded Generator drives every
    stochastic draw (PRD Section 7) -- never bare numpy.random."""
    rng = np.random.default_rng(seed)
    n = len(demands)  # customer count (depot excluded, PRD Section 9's R^N)

    positions = rng.uniform(-1.0, 1.0, size=(num_particles, n))
    if n > 1:
        # Warm start: a tenth of the swarm begins near the nearest-neighbour tour
        # (jittered), the rest stays random so exploration is not given up.
        seed_position = tour_to_position(nearest_neighbor_tour(time_matrix, n, depot_index), n)
        for i in range(max(1, num_particles // 10)):
            positions[i] = seed_position + rng.normal(0.0, 0.05, size=n)
    swarm_budget_s = time_budget_s * SWARM_SHARE
    pbest_positions = positions.copy()
    pbest_fitness = [None] * num_particles
    gbest_position = None
    gbest_fitness = None
    convergence_history: list[float] = []
    stagnation_counter = 0
    start = time.monotonic()
    stopped_reason = "max_iterations"
    # ponytail: running (expanding, never-shrinking) min/max across the whole
    # run -- PRD Section 11 says normalization is "tracked per-run", and a
    # per-ITERATION-only range makes every iteration's own best particle
    # trivially normalize to 0 (it *is* that iteration's min by definition),
    # which flattens the whole convergence signal to zero. Bug found via the
    # head-to-head verification script, not a test -- see EXPLAINABILITY.md.
    running_dist_range = None
    running_time_range = None

    iteration = 0
    for iteration in range(max_iterations):
        if time.monotonic() - start >= swarm_budget_s:
            stopped_reason = "time_budget"
            break

        alpha = 1.0 - (1.0 - 0.5) * (iteration / max_iterations) ** k
        lam = lambda_min + (lambda_max - lambda_min) * (iteration / max_iterations) ** k

        all_routes = [
            split_into_routes(rov_map(p), num_vehicles, time_matrix, depot_index) for p in positions
        ]
        all_distances = []
        all_times = []
        for routes in all_routes:
            d = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in routes)
            t = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in routes)
            all_distances.append(d)
            all_times.append(t)
        if running_dist_range is None:
            running_dist_range = (min(all_distances), max(all_distances))
            running_time_range = (min(all_times), max(all_times))
        else:
            running_dist_range = (min(running_dist_range[0], *all_distances), max(running_dist_range[1], *all_distances))
            running_time_range = (min(running_time_range[0], *all_times), max(running_time_range[1], *all_times))

        fitness_values = [
            evaluate_fitness(
                all_routes[i], distance_matrix, time_matrix, demands, vehicle_capacity,
                lam=lam, depot_index=depot_index, w_distance=w_distance, w_time=w_time,
                population_distance_range=running_dist_range, population_time_range=running_time_range,
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
        if progress_list is not None:
            progress_list.append(gbest_fitness.total)

        if stagnation_counter >= 50:
            positions, _ = reinitialize_stagnant_particles(positions, pbest_fitness, rng, fraction=0.2)
            stagnation_counter = 0

        mbest = pbest_positions.mean(axis=0)
        phi = rng.uniform(0.0, 1.0, size=(num_particles, n))
        attractor = phi * pbest_positions + (1 - phi) * gbest_position
        u = rng.uniform(1e-12, 1.0, size=(num_particles, n))  # avoid ln(1/0)
        sign = np.where(rng.random(size=(num_particles, n)) < 0.5, 1.0, -1.0)
        positions = attractor + sign * alpha * np.abs(mbest - positions) * np.log(1.0 / u)

    best_routes = split_into_routes(rov_map(gbest_position), num_vehicles, time_matrix, depot_index)
    # Exploit what the swarm found: iterated local search until the shared
    # budget runs out (or no further gain), instead of one fixed polish pass.
    # The local search minimizes the same blend the swarm does (PRD Section 11:
    # distance and time weighted w_distance / w_time), each normalized by the
    # swarm's own best solution, so the two stages optimize one objective.
    swarm_dist = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in best_routes)
    swarm_time = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in best_routes)
    blended = (
        w_distance * np.asarray(distance_matrix, dtype=float) / max(swarm_dist, 1e-9)
        + w_time * np.asarray(time_matrix, dtype=float) / max(swarm_time, 1e-9)
    )
    # Two polished candidates from the same swarm result -- one chasing time, one
    # the blended objective -- split the remaining budget evenly; QPSO keeps the
    # one with the lower estimated CO2 (the project's green objective, COPERT).
    now = time.monotonic()
    halfway = now + (start + time_budget_s - now) / 2
    candidates = [
        improve_routes(
            best_routes, matrix, demands, vehicle_capacity, depot_index,
            deadline=deadline, rng=np.random.default_rng(seed + 1 + i),
        )
        for i, (matrix, deadline) in enumerate(
            ((np.asarray(time_matrix, dtype=float), halfway), (blended, start + time_budget_s))
        )
    ]
    best_routes = min(
        candidates,
        key=lambda rs: _candidate_key(rs, distance_matrix, time_matrix, demands, vehicle_capacity, depot_index),
    )
    meta = {
        "seed": seed,
        "convergence_history": convergence_history,
        "iterations_run": iteration + 1,
        "stopped_reason": stopped_reason,
        "num_particles": num_particles,
        "swarm_share": SWARM_SHARE,
        "local_search": "iterated_local_search (time and blended candidates, kept by lower CO2)",
    }
    return best_routes, gbest_fitness, meta


def run_qpso_job(payload: dict, seed: int, time_budget_s: float, progress_list=None) -> dict:
    """SolverPort-shaped adapter over run_qpso. Converts QPSO's raw
    customer-index routes into Route objects (the shape run_ortools_job
    already returns) so the orchestrator can treat both uniformly."""
    node_ids = payload["node_ids"]
    depot_index = payload.get("depot_index", 0)
    routes, fitness, meta = run_qpso(
        payload["distance_matrix"], payload["time_matrix"], payload["demands"][1:],
        vehicle_capacity=payload["vehicle_capacity"], num_vehicles=payload["num_vehicles"],
        depot_index=depot_index, num_particles=payload.get("num_particles", 30),
        max_iterations=payload.get("max_iterations", 500), time_budget_s=time_budget_s, seed=seed,
        progress_list=progress_list,
    )
    route_objs = []
    for i, route in enumerate(routes):
        d, t = _route_distance_and_time(route, payload["distance_matrix"], payload["time_matrix"], depot_index)
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        route_objs.append(Route(vehicle_id=f"v{i}", node_sequence=stops, total_distance_m=d, total_time_s=t))
    meta["fitness_total"] = fitness.total
    return {"routes": route_objs, "meta": meta}
