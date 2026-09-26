"""Emissions delta between the OR-Tools baseline and QPSO routes on the
real Indiranagar test case, under identical seed/time-budget -- the
user's explicit Phase 4 ask."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.entities.route import Route
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp
from app.infrastructure.algorithms.qpso_solver import run_qpso, _route_distance_and_time
from app.infrastructure.algorithms.copert_model import (
    total_emissions_kg, co2_reduction_percent, EMISSION_FACTOR_SOURCE,
)

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
    print(f"Emission factor source: {EMISSION_FACTOR_SOURCE}\n")

    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(SEED)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    ortools_routes, _ = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_BUDGET_S,
    )
    ortools_co2_kg = total_emissions_kg(ortools_routes)

    qpso_routes, _, _ = run_qpso(
        dist, time_matrix, demands[1:], vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES,
        depot_index=0, num_particles=30, max_iterations=500, time_budget_s=TIME_BUDGET_S, seed=SEED,
    )
    # QPSO's routes are customer-index lists; wrap as Route objects for total_emissions_kg
    qpso_route_objs = []
    for i, route in enumerate(qpso_routes):
        d, t = _route_distance_and_time(route, dist, time_matrix, 0)
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        qpso_route_objs.append(Route(vehicle_id=f"v{i}", node_sequence=stops, total_distance_m=d, total_time_s=t))
    qpso_co2_kg = total_emissions_kg(qpso_route_objs)

    print(f"OR-Tools baseline CO2: {ortools_co2_kg:.4f} kg")
    print(f"QPSO CO2:              {qpso_co2_kg:.4f} kg")
    reduction = co2_reduction_percent(baseline_kg=ortools_co2_kg, optimized_kg=qpso_co2_kg)
    print(f"\nRelative CO2 reduction (QPSO vs. OR-Tools): {reduction:+.2f}%")
    print("(Primary reported metric per user decision 2026-09-27 -- absolute kg above is secondary,")
    print(" European-fleet-calibrated context, not a precise India-specific figure.)")
