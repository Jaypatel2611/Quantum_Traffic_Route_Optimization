"""Standalone, offline, no-network verification of the full Phase 1 pipeline
against the pre-cached Indiranagar graph — run manually, not part of the test suite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"

# 5 hand-picked points scattered across Indiranagar's road network.
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412)),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440)),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380)),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390)),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430)),
]

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    print(f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    dist, time = build_distance_time_matrix(graph, TEST_NODES)
    print("\nDistance matrix (meters):")
    print(np.round(dist, 1))
    print("\nBase time matrix (seconds):")
    print(np.round(time, 1))

    rng = np.random.default_rng(42)
    delayed_time = inject_stochastic_delay(time, rng, hour_of_day=8.0)
    print("\nTime matrix with 8am peak-hour stochastic delay (seconds):")
    print(np.round(delayed_time, 1))
