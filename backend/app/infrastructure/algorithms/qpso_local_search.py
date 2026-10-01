"""Memetic helpers for QPSO: a warm-start tour for the swarm and a bounded
iterated local search that polishes the swarm's best routes.

The swarm explores globally; this module exploits. Everything is deadline-
bounded so QPSO's total wall-clock stays inside the shared time budget (the
same budget OR-Tools gets), and every move keeps each customer on exactly one
route. Routes are lists of 0-based customer indices; matrix index = customer + 1.
Cost is the route cost under whatever matrix the caller passes (QPSO passes its
blended distance/time objective) plus a steep penalty for capacity overload, so an over-capacity swarm solution is repaired
before anything else improves."""
import time

import numpy as np

_OVERLOAD_PENALTY = 1e6  # per unit of demand over capacity; dwarfs any route time


def nearest_neighbor_tour(time_matrix, num_customers: int, depot_index: int = 0) -> list[int]:
    """Greedy giant tour: from the depot, always visit the quickest unvisited customer."""
    remaining = set(range(num_customers))
    tour: list[int] = []
    here = depot_index
    while remaining:
        nxt = min(remaining, key=lambda c: time_matrix[here][c + 1])
        tour.append(nxt)
        remaining.remove(nxt)
        here = nxt + 1
    return tour


def tour_to_position(tour: list[int], num_customers: int) -> np.ndarray:
    """Inverse of the swarm's rank-order mapping: a position whose argsort is `tour`."""
    position = np.empty(num_customers)
    for rank, customer in enumerate(tour):
        position[customer] = -1.0 + 2.0 * rank / max(num_customers - 1, 1)
    return position


def _nodes(route: list[int], depot: int) -> list[int]:
    return [depot] + [c + 1 for c in route] + [depot]


def _route_time(route: list[int], T, depot: int) -> float:
    nodes = _nodes(route, depot)
    return float(sum(T[a][b] for a, b in zip(nodes, nodes[1:])))


def solution_cost(routes: list[list[int]], T, demands, capacity: float, depot: int) -> float:
    cost = sum(_route_time(r, T, depot) for r in routes)
    for r in routes:
        cost += _OVERLOAD_PENALTY * max(0.0, sum(demands[c] for c in r) - capacity)
    return cost


def _two_opt(route: list[int], T, depot: int, deadline: float) -> list[int]:
    """Within-route 2-opt with O(1) move evaluation (asymmetric-safe prefix sums)."""
    if len(route) < 3:
        return route
    s = _nodes(route, depot)
    while time.monotonic() < deadline:
        forward = np.concatenate(([0.0], np.cumsum([T[s[i]][s[i + 1]] for i in range(len(s) - 1)])))
        backward = np.concatenate(([0.0], np.cumsum([T[s[i + 1]][s[i]] for i in range(len(s) - 1)])))
        best, move = -1e-9, None
        for i in range(1, len(s) - 2):
            for j in range(i + 1, len(s) - 1):
                old = T[s[i - 1]][s[i]] + (forward[j] - forward[i]) + T[s[j]][s[j + 1]]
                new = T[s[i - 1]][s[j]] + (backward[j] - backward[i]) + T[s[i]][s[j + 1]]
                if new - old < best:
                    best, move = new - old, (i, j)
        if move is None:
            break
        i, j = move
        s[i:j + 1] = s[i:j + 1][::-1]
    return [c - 1 for c in s[1:-1]]


def _tables(routes: list[list[int]], depot: int, n: int):
    """Arc arrays over every route (P->Q), plus where each customer currently sits."""
    P, Q, R, POS = [], [], [], []
    rc = np.empty(n, dtype=int)
    pc = np.empty(n, dtype=int)
    prev = np.empty(n, dtype=int)
    nxt = np.empty(n, dtype=int)
    for r, route in enumerate(routes):
        nodes = _nodes(route, depot)
        for i in range(len(nodes) - 1):
            P.append(nodes[i])
            Q.append(nodes[i + 1])
            R.append(r)
            POS.append(i)
        for i, c in enumerate(route):
            rc[c], pc[c], prev[c], nxt[c] = r, i, nodes[i], nodes[i + 2]
    return np.array(P), np.array(Q), np.array(R), np.array(POS), rc, pc, prev, nxt


def _relocate_descent(routes, loads, T, dem, capacity, depot, deadline) -> None:
    """Best-improvement customer relocation (any route, any position), fully
    vectorized: every (customer, insertion arc) pair is scored in one numpy
    expression, then the single best strictly-improving move is applied."""
    n = len(dem)
    if n == 0:
        return
    cidx = np.arange(n) + 1
    while time.monotonic() < deadline:
        P, Q, R, POS, rc, pc, prev, nxt = _tables(routes, depot, n)
        removal = T[prev, cidx] + T[cidx, nxt] - T[prev, nxt]  # time saved by lifting c out
        insertion = T[np.ix_(P, cidx)].T + T[np.ix_(cidx, Q)] - T[P, Q][None, :]
        total = insertion - removal[:, None]

        load = np.asarray(loads, dtype=float)
        over = np.maximum(0.0, load - capacity)
        leave = _OVERLOAD_PENALTY * (np.maximum(0.0, load[rc] - dem - capacity) - over[rc])
        enter = _OVERLOAD_PENALTY * (np.maximum(0.0, load[R][None, :] + dem[:, None] - capacity) - over[R][None, :])
        same = R[None, :] == rc[:, None]
        total = total + np.where(same, 0.0, leave[:, None] + enter)
        # Re-inserting next to its own current neighbours is a no-op, not a move.
        total[same & ((POS[None, :] == pc[:, None]) | (POS[None, :] == pc[:, None] + 1))] = np.inf

        flat = int(np.argmin(total))
        c, e = divmod(flat, total.shape[1])
        if total[c, e] >= -1e-9:
            return
        src, src_pos, dst, dst_pos = int(rc[c]), int(pc[c]), int(R[e]), int(POS[e])
        routes[src].pop(src_pos)
        if dst == src and dst_pos > src_pos:
            dst_pos -= 1
        routes[dst].insert(dst_pos, c)
        loads[src] -= dem[c]
        loads[dst] += dem[c]


def _best_insert(c: int, routes, loads, T, dem, capacity, depot) -> None:
    """Cheapest-insertion of one customer (capacity-penalized)."""
    P, Q, R, POS = _arc_only(routes, depot)
    cost = T[P, c + 1] + T[c + 1, Q] - T[P, Q]
    load = np.asarray(loads, dtype=float)
    cost = cost + _OVERLOAD_PENALTY * (
        np.maximum(0.0, load[R] + dem[c] - capacity) - np.maximum(0.0, load[R] - capacity)
    )
    e = int(np.argmin(cost))
    routes[int(R[e])].insert(int(POS[e]), c)
    loads[int(R[e])] += dem[c]


def _arc_only(routes, depot):
    P, Q, R, POS = [], [], [], []
    for r, route in enumerate(routes):
        nodes = _nodes(route, depot)
        for i in range(len(nodes) - 1):
            P.append(nodes[i])
            Q.append(nodes[i + 1])
            R.append(r)
            POS.append(i)
    return np.array(P), np.array(Q), np.array(R), np.array(POS)


def _descend(routes, loads, T, dem, capacity, depot, deadline) -> None:
    _relocate_descent(routes, loads, T, dem, capacity, depot, deadline)
    for r in range(len(routes)):
        routes[r] = _two_opt(routes[r], T, depot, deadline)
    _relocate_descent(routes, loads, T, dem, capacity, depot, deadline)


def improve_routes(
    routes: list[list[int]],
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    depot_index: int,
    deadline: float,
    rng: np.random.Generator,
    patience: int = 5000,
) -> list[list[int]]:
    """Iterated local search from the swarm's best routes: descend, then repeat
    ruin-and-recreate (lift a few nearby customers out, cheapest-insert them
    back in random order) + descend, keeping a result only if it is strictly
    better. Stops at the deadline or after `patience` rounds without a gain,
    so tiny instances finish early."""
    T = np.asarray(time_matrix, dtype=float)
    dem = np.asarray(demands, dtype=float)
    n = len(dem)
    routes = [list(r) for r in routes]
    if n == 0:
        return routes
    loads = [float(sum(dem[c] for c in r)) for r in routes]
    _descend(routes, loads, T, dem, vehicle_capacity, depot_index, deadline)

    cidx = np.arange(n) + 1
    near = np.argsort(T[np.ix_(cidx, cidx)] + T[np.ix_(cidx, cidx)].T, axis=1)  # [c] -> customers by closeness
    best = [list(r) for r in routes]
    best_cost = solution_cost(best, T, dem, vehicle_capacity, depot_index)
    stale = 0
    while time.monotonic() < deadline and stale < patience:
        cur = [list(r) for r in best]
        cur_loads = [float(sum(dem[c] for c in r)) for r in cur]
        k = int(rng.integers(2, min(8, n) + 1))
        seed_customer = int(rng.integers(n))
        removed = [int(c) for c in near[seed_customer][:k]]
        for c in removed:
            for r, route in enumerate(cur):
                if c in route:
                    route.remove(c)
                    cur_loads[r] -= dem[c]
                    break
        rng.shuffle(removed)
        for c in removed:
            _best_insert(c, cur, cur_loads, T, dem, vehicle_capacity, depot_index)
        _descend(cur, cur_loads, T, dem, vehicle_capacity, depot_index, deadline)
        cost = solution_cost(cur, T, dem, vehicle_capacity, depot_index)
        if cost < best_cost - 1e-9:
            best, best_cost, stale = cur, cost, 0
        else:
            stale += 1
    return best
