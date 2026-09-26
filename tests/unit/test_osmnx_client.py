import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.infrastructure.geospatial.osmnx_client import (
    FALLBACK_SPEED_KMH,
    HWY_SPEEDS_KMH,
    fetch_and_cache_graph,
)


@patch("app.infrastructure.geospatial.osmnx_client.ox")
def test_rejects_oversized_place_before_fetching(mock_ox, tmp_path):
    oversized_gdf = MagicMock()
    oversized_gdf.to_crs.return_value.area.iloc.__getitem__.return_value = 500_000_000  # m^2, way over cap
    mock_ox.geocode_to_gdf.return_value = oversized_gdf

    with pytest.raises(ValueError, match="too large"):
        fetch_and_cache_graph("India", tmp_path / "india.graphml", max_place_area_km2=50.0)

    mock_ox.graph_from_place.assert_not_called()


@patch("app.infrastructure.geospatial.osmnx_client.ox")
def test_fetches_truncates_and_caches_valid_place(mock_ox, tmp_path):
    small_gdf = MagicMock()
    small_gdf.to_crs.return_value.area.iloc.__getitem__.return_value = 2_000_000  # 2 km^2
    mock_ox.geocode_to_gdf.return_value = small_gdf

    raw_graph = MagicMock(name="raw_graph")
    truncated_graph = MagicMock(name="truncated_graph")
    with_speeds = MagicMock(name="with_speeds")
    with_times = MagicMock(name="with_times")
    mock_ox.graph_from_place.return_value = raw_graph
    mock_ox.truncate.largest_component.return_value = truncated_graph
    mock_ox.add_edge_speeds.return_value = with_speeds
    mock_ox.add_edge_travel_times.return_value = with_times

    cache_path = tmp_path / "koramangala.graphml"
    fetch_and_cache_graph("Koramangala, Bengaluru, India", cache_path)

    mock_ox.graph_from_place.assert_called_once_with("Koramangala, Bengaluru, India", network_type="drive")
    mock_ox.truncate.largest_component.assert_called_once_with(raw_graph, strongly=True)
    mock_ox.add_edge_speeds.assert_called_once_with(
        truncated_graph, hwy_speeds=HWY_SPEEDS_KMH, fallback=FALLBACK_SPEED_KMH
    )
    mock_ox.add_edge_travel_times.assert_called_once_with(with_speeds)
    mock_ox.save_graphml.assert_called_once_with(with_times, filepath=str(cache_path))
