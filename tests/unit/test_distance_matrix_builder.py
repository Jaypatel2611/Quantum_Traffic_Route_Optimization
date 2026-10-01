import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import networkx as nx
import numpy as np
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import (
    build_accident_impacts,
    FastestPaths,
    build_distance_time_matrix,
    build_route_geometries,
)


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


def test_route_geometry_follows_graph_junctions_not_a_straight_line():
    """Route n1 -> n3 must pass through junction 2 (the only road), and start/end at the stops."""
    nodes = [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n3", coordinates=GeographicCoordinates(lat=12.92, lon=77.62)),
    ]
    [geometry] = build_route_geometries(_asymmetric_graph(), nodes, [["n1", "n3"]])
    assert [12.91, 77.61] in geometry
    assert geometry[0] == [12.90, 77.60]
    assert geometry[-1] == [12.92, 77.62]


def test_route_geometry_detours_around_accident_edge():
    """Two parallel roads 1->3: via junction 2 (fast) or via junction 4 (slower). Blocking 1-2 (x5 time) flips the path to 4."""
    g = nx.MultiDiGraph()
    for nid, y, x in [(1, 12.90, 77.60), (2, 12.91, 77.61), (3, 12.92, 77.62), (4, 12.93, 77.60)]:
        g.add_node(nid, y=y, x=x)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 3, length=500, travel_time=60)
    g.add_edge(1, 4, length=600, travel_time=100)
    g.add_edge(4, 3, length=600, travel_time=100)
    g.graph["crs"] = "epsg:4326"
    nodes = [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n3", coordinates=GeographicCoordinates(lat=12.92, lon=77.62)),
    ]
    [free] = build_route_geometries(g, nodes, [["n1", "n3"]])
    g[1][2][0]["travel_time"] *= 5
    [blocked] = build_route_geometries(g, nodes, [["n1", "n3"]])
    assert [12.91, 77.61] in free and [12.93, 77.60] not in free
    assert [12.93, 77.60] in blocked and [12.91, 77.61] not in blocked


def _two_route_graph(alt_time: float):
    """1-2-3 is fast (60+60); 1-4-3 is the alternative (alt_time per leg)."""
    g = nx.MultiDiGraph()
    for nid, y, x in [(1, 12.90, 77.60), (2, 12.91, 77.61), (3, 12.92, 77.62), (4, 12.93, 77.60), (5, 12.95, 77.65)]:
        g.add_node(nid, y=y, x=x)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 3, length=500, travel_time=60)
    g.add_edge(3, 5, length=300, travel_time=30)  # dead-end spur no route uses
    g.add_edge(1, 4, length=600, travel_time=alt_time)
    g.add_edge(4, 3, length=600, travel_time=alt_time)
    g.graph["crs"] = "epsg:4326"
    return g


def _impacts(graph, accidents):
    nodes = [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n3", coordinates=GeographicCoordinates(lat=12.92, lon=77.62)),
    ]
    return build_accident_impacts(graph, nodes, [["n1", "n3"]], accidents, multiplier=5.0)


def test_accident_with_a_cheaper_way_around_is_rerouted_with_the_extra_time():
    [impact] = _impacts(_two_route_graph(alt_time=100), [(1, 2)])
    # free 60+60=120; with 1-2 at 300 the alternative 100+100=200 wins -> +80
    assert impact["status"] == "rerouted"
    assert impact["added_time_s"] == 80


def test_accident_with_no_cheaper_way_around_is_driven_through_slower():
    [impact] = _impacts(_two_route_graph(alt_time=1000), [(1, 2)])
    assert impact["status"] == "driven_through"
    assert impact["added_time_s"] == 240  # 1-2 goes 60 -> 300


def test_accident_off_every_route_has_no_effect_and_each_accident_is_judged_separately():
    on, off = _impacts(_two_route_graph(alt_time=100), [(2, 3), (3, 5)])
    assert on["status"] == "rerouted"
    assert off == {"from_node_id": 3, "to_node_id": 5, "status": "not_on_route", "added_time_s": 0.0}


def test_a_second_accident_that_blocks_the_detour_turns_a_reroute_into_driven_through():
    # Alone, 2-3 is avoidable via 1-4-3; with 1-4 also blocked there is no cheaper way around.
    on, _ = _impacts(_two_route_graph(alt_time=100), [(2, 3), (1, 4)])
    assert on["status"] == "driven_through"


def _fast_but_long_graph():
    """1->3: via 2 is fast (120 s) but long (2000 m); via 4 is slow (300 s) but short (1200 m)."""
    g = nx.MultiDiGraph()
    for nid, y, x in [(1, 12.90, 77.60), (2, 12.91, 77.61), (3, 12.92, 77.62), (4, 12.93, 77.60)]:
        g.add_node(nid, y=y, x=x)
    g.add_edge(1, 2, length=1000, travel_time=60)
    g.add_edge(2, 3, length=1000, travel_time=60)
    g.add_edge(1, 4, length=600, travel_time=150)
    g.add_edge(4, 3, length=600, travel_time=150)
    g.add_edge(3, 1, length=5000, travel_time=900)  # the real graph is strongly connected
    g.graph["crs"] = "epsg:4326"
    return g


def _n1_n3():
    return [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n3", coordinates=GeographicCoordinates(lat=12.92, lon=77.62)),
    ]


def test_distance_is_the_length_of_the_fastest_path_not_the_shortest_one():
    dist, time = build_distance_time_matrix(_fast_but_long_graph(), _n1_n3())
    assert time[0, 1] == 120
    assert dist[0, 1] == 2000  # the road actually driven, not the 1200 m shortcut nobody takes


def test_an_accident_that_forces_a_detour_changes_the_distance_too():
    g = _fast_but_long_graph()
    g[1][2][0]["travel_time"] *= 5  # accident on 1-2 -> 300 + 60 beats nothing; via 4 is 300 total
    dist, time = build_distance_time_matrix(g, _n1_n3())
    assert time[0, 1] == 300
    assert dist[0, 1] == 1200


def test_matrix_distance_equals_the_length_along_the_drawn_path():
    g = _fast_but_long_graph()
    nodes = _n1_n3()
    dist, _ = build_distance_time_matrix(g, nodes)
    path = FastestPaths(g).path(1, 3)
    drawn_length = sum(g[u][v][0]["length"] for u, v in zip(path, path[1:]))
    assert path == [1, 2, 3]
    assert dist[0, 1] == drawn_length


def test_parallel_edges_use_the_fastest_ones_length():
    g = nx.MultiDiGraph()
    for nid, y, x in [(1, 12.90, 77.60), (2, 12.91, 77.61)]:
        g.add_node(nid, y=y, x=x)
    g.add_edge(1, 2, length=900, travel_time=40)  # slower road, shorter ...
    g.add_edge(1, 2, length=1500, travel_time=30)  # ... faster road, longer: the one driven
    g.add_edge(2, 1, length=1500, travel_time=30)
    g.graph["crs"] = "epsg:4326"
    nodes = [
        Node(id="a", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="b", coordinates=GeographicCoordinates(lat=12.91, lon=77.61)),
    ]
    dist, time = build_distance_time_matrix(g, nodes)
    assert time[0, 1] == 30 and dist[0, 1] == 1500
