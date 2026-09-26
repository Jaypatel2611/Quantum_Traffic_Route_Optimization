from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.domain.entities.route import Route

# Confirmed by direct inspection of ortools==9.15.6755's RoutingSearchParameters
# proto field list: there is no random_seed field. Per PRD Section 7, this is a
# known limitation to surface explicitly, not a silent gap — the fairness
# comparison with QPSO (Phase 3) is time-budget-matched, not RNG-state-matched,
# on the OR-Tools side.
SEED_CONFIGURABLE = False


def solve_cvrp(
    time_matrix,
    distance_matrix,
    node_ids: list[str],
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    depot_index: int = 0,
    time_limit_s: float = 5.0,
) -> tuple[list[Route], dict]:
    """CVRP via OR-Tools, optimizing on time (PRD Section 9.2): PATH_CHEAPEST_ARC
    first-solution strategy, GUIDED_LOCAL_SEARCH metaheuristic, hard time limit."""
    n = len(node_ids)
    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(round(time_matrix[from_node][to_node]))

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [int(vehicle_capacity)] * num_vehicles, True, "Capacity"
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(int(round(time_limit_s)))

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        raise RuntimeError(
            f"OR-Tools found no feasible solution within time_limit_s={time_limit_s} "
            f"(vehicle_capacity={vehicle_capacity}, num_vehicles={num_vehicles}) — "
            "check that capacity * num_vehicles covers total demand."
        )

    routes: list[Route] = []
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        sequence = [node_ids[manager.IndexToNode(index)]]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            sequence.append(node_ids[manager.IndexToNode(index)])
        if len(sequence) <= 2:  # depot -> depot only: this vehicle was unused
            continue

        total_distance_m = sum(
            distance_matrix[node_ids.index(a)][node_ids.index(b)]
            for a, b in zip(sequence, sequence[1:])
        )
        total_time_s = sum(
            time_matrix[node_ids.index(a)][node_ids.index(b)]
            for a, b in zip(sequence, sequence[1:])
        )
        routes.append(
            Route(
                vehicle_id=f"v{vehicle_id}",
                node_sequence=sequence,
                total_distance_m=float(total_distance_m),
                total_time_s=float(total_time_s),
            )
        )

    meta = {
        "seed_configurable": SEED_CONFIGURABLE,
        "time_limit_s": time_limit_s,
        "first_solution_strategy": "PATH_CHEAPEST_ARC",
        "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
    }
    return routes, meta


def run_ortools_job(payload: dict, seed: int, time_budget_s: float) -> dict:
    """SolverPort-shaped adapter over solve_cvrp. `seed` is accepted for a
    uniform call signature with run_qpso_job; unused here because
    RoutingSearchParameters has no random_seed field (see SEED_CONFIGURABLE)."""
    routes, meta = solve_cvrp(
        payload["time_matrix"], payload["distance_matrix"], payload["node_ids"], payload["demands"],
        vehicle_capacity=payload["vehicle_capacity"], num_vehicles=payload["num_vehicles"],
        depot_index=payload.get("depot_index", 0), time_limit_s=time_budget_s,
    )
    return {"routes": routes, "meta": meta}
