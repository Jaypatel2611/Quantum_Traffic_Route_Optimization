import time

import numpy as np

from app.domain.entities.route import Route
from app.domain.value_objects.fitness_score import FitnessScore


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


def _stops_time(stops: list[int], time_matrix) -> float:
    return sum(time_matrix[a][b] for a, b in zip(stops, stops[1:]))


def two_opt_route(route: list[int], time_matrix, depot_index: int = 0, max_passes: int = 100) -> list[int]:
    """Classic 2-opt local search, reordering customers *within* one route
    to reduce total time (never moving a customer to a different route, so
    capacity/demand per route is untouched). QPSO's ROV/continuous-position
    encoding plus the DP split gives a globally-explored route grouping and
    a cost-minimizing cut of a fixed tour order, but neither ever locally
    polishes the resulting visiting order the way OR-Tools's own
    GUIDED_LOCAL_SEARCH continuously does -- found to be the real gap after
    the split fix and a correctly-forwarded higher particle count still
    left QPSO's real routes far worse than OR-Tools's even with 4000+
    iterations and a 60s budget (not a search-depth problem, a missing
    refinement step). Runs once on the final best routes, not per-particle
    per-iteration -- cheap at typical per-vehicle route lengths, and it
    would defeat the point of comparing QPSO's own swarm search against
    OR-Tools if it ran inside the fitness-evaluation hot loop instead."""
    if len(route) < 3:
        return route
    stops = [depot_index] + [c + 1 for c in route] + [depot_index]
    for _ in range(max_passes):
        improved = False
        for i in range(1, len(stops) - 2):
            for j in range(i + 1, len(stops) - 1):
                candidate = stops[:i] + stops[i:j + 1][::-1] + stops[j + 1:]
                if _stops_time(candidate, time_matrix) < _stops_time(stops, time_matrix) - 1e-9:
                    stops = candidate
                    improved = True
        if not improved:
            break
    return [c - 1 for c in stops[1:-1]]


def _route_time(route: list[int], time_matrix, depot_index: int = 0) -> float:
    stops = [depot_index] + [c + 1 for c in route] + [depot_index]
    return _stops_time(stops, time_matrix)


def _route_load(route: list[int], demands: list[float]) -> float:
    return sum(demands[i] for i in route)


def relocate_and_swap_polish(
    routes: list[list[int]],
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    depot_index: int = 0,
    max_passes: int = 30,
) -> list[list[int]]:
    """Or-opt (single-customer relocate) + pairwise swap local search
    BETWEEN routes -- the piece neither the DP split (cuts a fixed tour
    order, never moves a customer across routes) nor two_opt_route (only
    reorders within one already-fixed customer set) can reach.

    This is the actual remaining gap found via the bigger demo-scenario
    verification: even after the split and two-opt fixes, and even with
    150 particles and a 60s budget (4000+ iterations), QPSO's real routes
    stayed far worse than OR-Tools's, because *which* customer ends up on
    *which* vehicle still depends entirely on where the swarm's continuous
    position happened to rank it -- a bad initial assignment the swarm
    never escaped. This polish pass fixes that directly, after the fact,
    the same way two_opt_route polishes visiting order after the fact.

    Capacity is enforced here (unlike split/evaluate_fitness's soft
    penalty) because a move that violates it is simply rejected outright
    -- there is no swarm exploration benefit to accepting an infeasible
    move in a deterministic post-hoc polish step."""
    routes = [list(r) for r in routes]
    num_routes = len(routes)

    for _ in range(max_passes):
        improved = False
        for i in range(num_routes):
            for j in range(num_routes):
                if i == j:
                    continue
                load_j = _route_load(routes[j], demands)

                # Relocate: move one customer from routes[i] into the
                # cheapest position of routes[j].
                for c in list(routes[i]):
                    if c not in routes[i] or load_j + demands[c] > vehicle_capacity:
                        continue
                    without_i = [x for x in routes[i] if x != c]
                    base_time = _route_time(without_i, time_matrix, depot_index)
                    best_pos, best_total = None, None
                    for pos in range(len(routes[j]) + 1):
                        candidate_j = routes[j][:pos] + [c] + routes[j][pos:]
                        total = base_time + _route_time(candidate_j, time_matrix, depot_index)
                        if best_total is None or total < best_total:
                            best_total, best_pos = total, pos
                    current = _route_time(routes[i], time_matrix, depot_index) + _route_time(
                        routes[j], time_matrix, depot_index
                    )
                    if best_total is not None and best_total < current - 1e-9:
                        routes[i] = without_i
                        routes[j] = routes[j][:best_pos] + [c] + routes[j][best_pos:]
                        load_j = _route_load(routes[j], demands)
                        improved = True

                # Swap: exchange one customer between routes[i] and
                # routes[j] -- catches improving moves relocate alone
                # can't (both routes stay the same size, so a capacity-tight
                # pair can still improve without either exceeding it).
                for c1 in list(routes[i]):
                    if c1 not in routes[i]:
                        continue
                    for c2 in list(routes[j]):
                        # The lists were snapshotted before this loop; a swap
                        # earlier in it already moved c1 / changed routes[j].
                        # Acting on a stale id duplicates one customer and
                        # drops another (and looks cheaper, so it was accepted).
                        if c1 not in routes[i]:
                            break
                        if c2 not in routes[j]:
                            continue
                        load_i_after = _route_load(routes[i], demands) - demands[c1] + demands[c2]
                        load_j_after = load_j - demands[c2] + demands[c1]
                        if load_i_after > vehicle_capacity or load_j_after > vehicle_capacity:
                            continue
                        swapped_i = [c2 if x == c1 else x for x in routes[i]]
                        swapped_j = [c1 if x == c2 else x for x in routes[j]]
                        current = _route_time(routes[i], time_matrix, depot_index) + _route_time(
                            routes[j], time_matrix, depot_index
                        )
                        candidate = _route_time(swapped_i, time_matrix, depot_index) + _route_time(
                            swapped_j, time_matrix, depot_index
                        )
                        if candidate < current - 1e-9:
                            routes[i], routes[j] = swapped_i, swapped_j
                            load_j = _route_load(routes[j], demands)
                            improved = True
        if not improved:
            break

    return [two_opt_route(r, time_matrix, depot_index) for r in routes]


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
        if time.monotonic() - start >= time_budget_s:
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
    best_routes = [two_opt_route(r, time_matrix, depot_index) for r in best_routes]
    best_routes = relocate_and_swap_polish(
        best_routes, time_matrix, demands, vehicle_capacity, depot_index
    )
    meta = {
        "seed": seed,
        "convergence_history": convergence_history,
        "iterations_run": iteration + 1,
        "stopped_reason": stopped_reason,
        "num_particles": num_particles,
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
