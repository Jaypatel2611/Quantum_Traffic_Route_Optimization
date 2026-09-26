import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import networkx as nx
import numpy as np
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix


def test_no_infinite_distance_after_largest_component_cleaning():
    """A graph with a disconnected fragment must not throw once reduced to its largest
    strongly connected component first — this is PRD Section 10 point 2's guarantee,
    re-verified here at the matrix-builder boundary."""
    g = nx.MultiDiGraph()
    g.add_node(1, y=12.90, x=77.60)
    g.add_node(2, y=12.91, x=77.61)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 1, length=500, travel_time=60)
    g.add_node(99, y=20.0, x=80.0)  # disconnected fragment, no edges
    g.graph["crs"] = "epsg:4326"

    largest_scc_nodes = max(nx.strongly_connected_components(g), key=len)
    cleaned = g.subgraph(largest_scc_nodes).copy()

    nodes = [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n2", coordinates=GeographicCoordinates(lat=12.91, lon=77.61)),
    ]
    dist, time = build_distance_time_matrix(cleaned, nodes)
    assert np.all(np.isfinite(dist))
    assert np.all(np.isfinite(time))
