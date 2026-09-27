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
