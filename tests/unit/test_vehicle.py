import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.vehicle import Vehicle


def test_vehicle_constructs_with_defaults():
    v = Vehicle(id="v1", capacity=100.0)
    assert v.fuel_type == "diesel"


def test_zero_or_negative_capacity_raises():
    with pytest.raises(ValueError):
        Vehicle(id="v1", capacity=0.0)
    with pytest.raises(ValueError):
        Vehicle(id="v1", capacity=-10.0)
