"""Diagnostic: why did num_particles=30 and num_particles=150 produce the
exact same result on the 60-node scenario? Runs QPSO in-process (no HTTP)
against real cached-graph data for full-precision comparison."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.infrastructure.algorithms.qpso_solver import run_qpso

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"
CSV_PATH = Path(__file__).resolve().parents[2] / "docs" / "demo_scenarios" / "indiranagar_60.csv"

with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))
nodes = [Node(id=r["node_id"], coordinates=GeographicCoordinates(lat=float(r["lat"]), lon=float(r["lon"])), demand=float(r["demand"])) for r in rows]

graph = load_cached_graph(CACHE_PATH)
distance_matrix, base_time = build_distance_time_matrix(graph, nodes)
rng = np.random.default_rng(42)
time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)
demands = [n.demand for n in nodes][1:]  # customer demands, depot excluded

for num_particles in (30, 150):
    routes, fitness, meta = run_qpso(
        distance_matrix, time_matrix, demands,
        vehicle_capacity=150.0, num_vehicles=9, depot_index=0,
        num_particles=num_particles, max_iterations=500, time_budget_s=15.0, seed=42,
    )
    flat = tuple(sorted(tuple(r) for r in routes))
    print(f"num_particles={num_particles}: fitness_total={fitness.total!r} "
          f"iterations={meta['iterations_run']} stopped={meta['stopped_reason']}")
    print(f"  routes checksum: {hash(flat)} first_route={routes[0][:5] if routes[0] else routes}")
