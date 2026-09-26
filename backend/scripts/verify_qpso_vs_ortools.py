"""Head-to-head QPSO vs. OR-Tools on the real Indiranagar test case, under
identical seed and wall-clock time budget (PRD Section 7's fairness protocol)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp
from app.infrastructure.algorithms.qpso_solver import run_qpso, _route_distance_and_time

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"

TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]
VEHICLE_CAPACITY = 100.0
NUM_VEHICLES = 2
TIME_BUDGET_S = 5.0
SEED = 42

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(SEED)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    ortools_routes, ortools_meta = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_BUDGET_S,
    )
    ortools_total_time = sum(r.total_time_s for r in ortools_routes)
    ortools_total_distance = sum(r.total_distance_m for r in ortools_routes)

    qpso_routes, qpso_fitness, qpso_meta = run_qpso(
        dist, time_matrix, demands[1:], vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES,
        depot_index=0, num_particles=30, max_iterations=500, time_budget_s=TIME_BUDGET_S, seed=SEED,
    )
    qpso_total_distance = sum(_route_distance_and_time(r, dist, time_matrix, 0)[0] for r in qpso_routes)
    qpso_total_time = sum(_route_distance_and_time(r, dist, time_matrix, 0)[1] for r in qpso_routes)

    print("=== OR-Tools baseline ===")
    print(f"config: {ortools_meta}")
    for r in ortools_routes:
        print(f"  {r.vehicle_id}: {' -> '.join(r.node_sequence)}  (dist {r.total_distance_m:.1f} m, time {r.total_time_s:.1f} s)")
    print(f"  total: {ortools_total_distance:.1f} m, {ortools_total_time:.1f} s")

    print("\n=== QPSO ===")
    print(f"config: {qpso_meta}")
    for i, route in enumerate(qpso_routes):
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        print(f"  v{i}: {' -> '.join(stops)}")
    print(f"  total: {qpso_total_distance:.1f} m, {qpso_total_time:.1f} s, fitness: {qpso_fitness.total:.4f}")

    print(f"\n=== Comparison (time, the shared optimization objective) ===")
    delta_pct = (qpso_total_time - ortools_total_time) / ortools_total_time * 100
    winner = "OR-Tools" if ortools_total_time < qpso_total_time else "QPSO"
    print(f"OR-Tools: {ortools_total_time:.1f} s | QPSO: {qpso_total_time:.1f} s | delta: {delta_pct:+.1f}% | winner: {winner}")
