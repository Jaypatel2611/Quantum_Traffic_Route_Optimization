import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


def test_node_constructs_with_defaults():
    node = Node(id="depot", coordinates=GeographicCoordinates(lat=12.9, lon=77.6))
    assert node.demand == 0.0


def test_negative_demand_raises():
    with pytest.raises(ValueError):
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.9, lon=77.6), demand=-5.0)
