import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import networkx as nx
import numpy as np
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix


def _asymmetric_graph():
    """A -> B is short (60s); B -> A is long (120s) via a one-way detour, mimicking a real one-way street."""
    g = nx.MultiDiGraph()
    g.add_node(1, y=12.90, x=77.60)
    g.add_node(2, y=12.91, x=77.61)
    g.add_node(3, y=12.92, x=77.62)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 3, length=500, travel_time=60)
    g.add_edge(3, 1, length=1000, travel_time=120)
    g.graph["crs"] = "epsg:4326"
    return g


def _nodes():
    return [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n2", coordinates=GeographicCoordinates(lat=12.91, lon=77.61)),
    ]


def test_matrix_shape_is_n_by_n():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert dist.shape == (2, 2)
    assert time.shape == (2, 2)


def test_matrix_is_asymmetric_for_one_way_topology():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert time[0, 1] != time[1, 0]


def test_diagonal_is_zero():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert np.all(np.diag(dist) == 0)
    assert np.all(np.diag(time) == 0)
