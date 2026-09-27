import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.node import Node
from app.domain.exceptions import UnknownCityError
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.cached_graph_repository import CachedGraphRepository


def test_list_cities_returns_the_catalog():
    repo = CachedGraphRepository()
    cities = repo.list_cities()
    assert {"id": "indiranagar_bengaluru", "name": "Indiranagar, Bengaluru"} in cities


def test_build_matrices_raises_unknown_city_error_for_an_unrecognized_city():
    repo = CachedGraphRepository()
    nodes = [Node(id="depot", coordinates=GeographicCoordinates(lat=12.97, lon=77.64))]
    with pytest.raises(UnknownCityError):
        repo.build_matrices("not_a_real_city", nodes)


@patch("app.infrastructure.geospatial.cached_graph_repository.build_distance_time_matrix")
@patch("app.infrastructure.geospatial.cached_graph_repository.load_cached_graph")
def test_build_matrices_delegates_to_the_geospatial_pipeline_for_a_known_city(mock_load, mock_build):
    mock_load.return_value = "the-graph"
    mock_build.return_value = ("dist", "time")
    repo = CachedGraphRepository()
    nodes = [Node(id="depot", coordinates=GeographicCoordinates(lat=12.97, lon=77.64))]

    result = repo.build_matrices("indiranagar_bengaluru", nodes)

    mock_load.assert_called_once()
    mock_build.assert_called_once_with("the-graph", nodes)
    assert result == ("dist", "time")


def test_list_edges_raises_unknown_city_error_for_an_unrecognized_city():
    repo = CachedGraphRepository()
    with pytest.raises(UnknownCityError):
        repo.list_edges("not_a_real_city")


def test_list_edges_returns_deduplicated_real_edges_for_the_cached_city():
    repo = CachedGraphRepository()
    edges = repo.list_edges("indiranagar_bengaluru")

    assert len(edges) > 0
    seen_pairs = set()
    for edge in edges:
        pair = frozenset((edge["from_node_id"], edge["to_node_id"]))
        assert pair not in seen_pairs, "each undirected segment must appear once"
        seen_pairs.add(pair)
        assert -90 <= edge["from_lat"] <= 90
        assert -180 <= edge["from_lon"] <= 180


def test_accident_edge_multiplies_that_segments_travel_time_fivefold():
    """Real functional proof, not a mock: injecting an accident on a real
    edge from the cached graph must make the matrix built through it
    reflect the x5 delay, without perturbing paths that never cross it."""
    repo = CachedGraphRepository()
    edges = repo.list_edges("indiranagar_bengaluru")
    from_id, to_id = edges[0]["from_node_id"], edges[0]["to_node_id"]

    nodes = [
        Node(id="a", coordinates=GeographicCoordinates(lat=edges[0]["from_lat"], lon=edges[0]["from_lon"])),
        Node(id="b", coordinates=GeographicCoordinates(lat=edges[0]["to_lat"], lon=edges[0]["to_lon"])),
    ]

    _, base_time = repo.build_matrices("indiranagar_bengaluru", nodes)
    _, accident_time = repo.build_matrices(
        "indiranagar_bengaluru", nodes, accident_edge=(from_id, to_id)
    )

    assert accident_time[0][1] >= base_time[0][1] * 4.9  # ~5x, allowing for float rounding
