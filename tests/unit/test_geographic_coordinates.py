import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


def test_valid_coordinates_construct():
    coords = GeographicCoordinates(lat=12.9352, lon=77.6146)
    assert coords.lat == 12.9352
    assert coords.lon == 77.6146


@pytest.mark.parametrize("lat,lon", [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)])
def test_out_of_bounds_coordinates_raise(lat, lon):
    with pytest.raises(ValueError):
        GeographicCoordinates(lat=lat, lon=lon)


def test_coordinates_are_immutable():
    coords = GeographicCoordinates(lat=12.9352, lon=77.6146)
    with pytest.raises(Exception):
        coords.lat = 0.0
