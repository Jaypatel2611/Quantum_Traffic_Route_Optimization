import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.presentation.schemas.optimize_request import CreateJobFromNodesRequest

_BASE = {
    "city_id": "c",
    "nodes": [{"id": "depot", "lat": 12.97, "lon": 77.64, "demand": 0}, {"id": "n1", "lat": 12.98, "lon": 77.65, "demand": 5}],
    "vehicle_capacity": 10,
    "num_vehicles": 1,
    "seed": 1,
    "time_budget_s": 1,
}
_A = {"from_node_id": 1, "to_node_id": 2}
_B = {"from_node_id": 3, "to_node_id": 4}


def _edges(request):
    return [(e.from_node_id, e.to_node_id) for e in request.accident_edges]


def test_legacy_single_accident_edge_is_accepted_and_merged_into_the_list():
    request = CreateJobFromNodesRequest(**_BASE, accident_edge=_A)
    assert _edges(request) == [(1, 2)]
    assert request.accident_edge is None


def test_legacy_field_is_added_to_an_existing_list_without_duplicating():
    assert _edges(CreateJobFromNodesRequest(**_BASE, accident_edges=[_B], accident_edge=_A)) == [(3, 4), (1, 2)]
    assert _edges(CreateJobFromNodesRequest(**_BASE, accident_edges=[_A], accident_edge=_A)) == [(1, 2)]


def test_no_accident_fields_means_no_accidents():
    assert CreateJobFromNodesRequest(**_BASE).accident_edges == []
