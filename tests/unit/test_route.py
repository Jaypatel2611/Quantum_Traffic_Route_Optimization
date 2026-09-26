import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.domain.entities.route import Route


def test_route_constructs():
    r = Route(vehicle_id="v1", node_sequence=["depot", "n1", "n2", "depot"], total_distance_m=1200.0, total_time_s=180.0)
    assert r.node_sequence[0] == r.node_sequence[-1] == "depot"
    assert r.total_distance_m == 1200.0
