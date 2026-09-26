"""Standalone, offline verification of the OR-Tools baseline against the
real cached Indiranagar graph and Phase 1's 5-node test case."""
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

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"

# Same 5 points as Phase 1's verification script, now with demands assigned.
# depot demand 0; n1..n4 demands chosen so total (130) needs 2 vehicles at
# capacity 100 each -- exercises the capacity constraint for real, not trivially.
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]
VEHICLE_CAPACITY = 100.0
NUM_VEHICLES = 2
TIME_LIMIT_S = 5.0  # PRD Section 7's cited example hard timeout

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(42)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    routes, meta = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_LIMIT_S,
    )

    print(f"Solver config: {meta}")
    print(f"\n{len(routes)} route(s) found:")
    for route in routes:
        print(f"  {route.vehicle_id}: {' -> '.join(route.node_sequence)}")
        print(f"    distance: {route.total_distance_m:.1f} m, time: {route.total_time_s:.1f} s")

    total_distance = sum(r.total_distance_m for r in routes)
    total_time = sum(r.total_time_s for r in routes)
    print(f"\nTotal across all routes: {total_distance:.1f} m, {total_time:.1f} s")
