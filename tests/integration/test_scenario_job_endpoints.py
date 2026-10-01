import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_NODES_PAYLOAD = {
    "city_id": "indiranagar_bengaluru",
    "nodes": [
        {"id": "depot", "lat": 12.9716, "lon": 77.6412, "demand": 0},
        {"id": "n1", "lat": 12.9750, "lon": 77.6440, "demand": 30},
        {"id": "n2", "lat": 12.9690, "lon": 77.6380, "demand": 40},
        {"id": "n3", "lat": 12.9760, "lon": 77.6390, "demand": 25},
        {"id": "n4", "lat": 12.9670, "lon": 77.6430, "demand": 35},
    ],
    "vehicle_capacity": 100.0,
    "num_vehicles": 2,
    "seed": 42,
    "time_budget_s": 1.5,
}


def test_list_cities_returns_the_one_cached_city():
    response = client.get("/cities")
    assert response.status_code == 200
    cities = response.json()
    assert {"id": "indiranagar_bengaluru", "name": "Indiranagar, Bengaluru"} in cities


def test_unknown_city_id_returns_404():
    payload = {**_NODES_PAYLOAD, "city_id": "not_a_real_city"}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 404


def test_unknown_job_id_result_returns_404():
    response = client.get("/jobs/not-a-real-job-id/result")
    assert response.status_code == 404


def test_too_few_nodes_returns_422():
    payload = {**_NODES_PAYLOAD, "nodes": _NODES_PAYLOAD["nodes"][:1]}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_non_positive_vehicle_capacity_returns_422():
    payload = {**_NODES_PAYLOAD, "vehicle_capacity": 0}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_non_positive_num_vehicles_returns_422():
    payload = {**_NODES_PAYLOAD, "num_vehicles": 0}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_invalid_node_coordinates_return_422_not_500():
    bad_nodes = [{**_NODES_PAYLOAD["nodes"][0]}, {**_NODES_PAYLOAD["nodes"][1], "lat": 200.0}]
    payload = {**_NODES_PAYLOAD, "nodes": bad_nodes}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_missing_node_field_returns_422_not_500():
    bad_nodes = [{**_NODES_PAYLOAD["nodes"][0]}, {"id": "n1", "lat": 12.97, "lon": 77.64}]
    del bad_nodes[1]["lon"]
    payload = {**_NODES_PAYLOAD, "nodes": bad_nodes}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_wrong_type_for_vehicle_capacity_returns_422():
    """Phase 7's real Pydantic schema rejects a type Phase 6's temporary
    dict-based endpoint would have let through unchecked (until it crashed
    deep inside the solver instead of at the request boundary)."""
    payload = {**_NODES_PAYLOAD, "vehicle_capacity": "a lot"}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 422


def test_openapi_schema_documents_the_real_endpoints():
    schema = client.get("/openapi.json").json()
    assert "/jobs/from-nodes" in schema["paths"]
    assert "/cities" in schema["paths"]
    assert "/jobs/{job_id}/result" in schema["paths"]
    assert "/cities/{city_id}/edges" in schema["paths"]


def test_list_edges_for_unknown_city_returns_404():
    response = client.get("/cities/not_a_real_city/edges")
    assert response.status_code == 404


def test_list_edges_returns_real_edges_for_the_cached_city():
    response = client.get("/cities/indiranagar_bengaluru/edges")
    assert response.status_code == 200
    edges = response.json()
    assert len(edges) > 0
    assert set(edges[0].keys()) == {
        "edge_id", "from_node_id", "to_node_id", "from_lat", "from_lon", "to_lat", "to_lon",
    }


def test_accident_edge_produces_a_slower_real_result_than_without_one():
    """Flow C end-to-end: injecting a real accident edge from the cached
    graph must genuinely change the solved routes' timing, and the result
    must echo back which edge was used for the Results screen's caption."""
    edges = client.get("/cities/indiranagar_bengaluru/edges").json()
    accident = next(e for e in edges if e["edge_id"] == edges[0]["edge_id"])

    payload = {**_NODES_PAYLOAD, "accident_edges": [{
        "from_node_id": accident["from_node_id"], "to_node_id": accident["to_node_id"],
    }]}
    response = client.post("/jobs/from-nodes", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 20.0
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        time.sleep(0.5)

    assert result["status"] == "done", f"job never completed: {result}"
    assert result["accident_edges"] == [{
        "from_node_id": accident["from_node_id"], "to_node_id": accident["to_node_id"],
    }]


def test_job_without_accidents_has_an_empty_accident_list_in_the_result():
    response = client.post("/jobs/from-nodes", json=_NODES_PAYLOAD)
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 20.0
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        time.sleep(0.5)

    assert result["status"] == "done"
    assert result["accident_edges"] == []


def test_from_nodes_job_builds_matrices_and_produces_a_comparable_result():
    """End-to-end: raw lat/lon nodes -> cached-graph matrix build -> both
    solvers -> a result payload the Results/Green Impact screens can render
    directly, with no client-side matrix building required."""
    response = client.post("/jobs/from-nodes", json=_NODES_PAYLOAD)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 20.0
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        time.sleep(0.5)

    assert result["status"] == "done", f"job never completed: {result}"
    assert len(result["ortools"]["routes"]) > 0
    assert len(result["qpso"]["routes"]) > 0
    assert result["ortools"]["total_co2_kg"] > 0
    assert result["qpso"]["total_co2_kg"] > 0
    green = result["green_impact"]
    assert green["co2_saved_kg"] == pytest.approx(
        result["ortools"]["total_co2_kg"] - result["qpso"]["total_co2_kg"]
    )
    assert green["fuel_saved_liters"] == pytest.approx(green["co2_saved_kg"] / 2.68)
    assert "emission_factor_source" in green


def test_num_particles_is_forwarded_to_the_qpso_solver():
    """Regression test: /jobs/from-nodes originally built its job payload
    without num_particles/max_iterations, so a caller's tuning request was
    silently dropped and every job ran with run_qpso_job's bare defaults
    regardless of what was asked for -- found via two HTTP requests with
    very different particle counts producing bit-identical results, not a
    test, until this one was added."""
    payload = {**_NODES_PAYLOAD, "num_particles": 7}
    response = client.post("/jobs/from-nodes", json=payload)
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 20.0
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        time.sleep(0.5)

    assert result["status"] == "done", f"job never completed: {result}"
    assert result["qpso"]["meta"]["num_particles"] == 7


def _wait_done(job_id: str) -> dict:
    deadline = time.monotonic() + 20.0
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        time.sleep(0.5)
    assert result["status"] == "done", f"job never completed: {result}"
    return result


def test_result_stops_match_the_route_order_and_sum_to_the_route_totals():
    job_id = client.post("/jobs/from-nodes", json=_NODES_PAYLOAD).json()["job_id"]
    result = _wait_done(job_id)

    for algo in ("ortools", "qpso"):
        for route in result[algo]["routes"]:
            stops = route["stops"]
            assert [s["node_id"] for s in stops] == route["node_sequence"]
            assert stops[0]["leg_distance_m"] == 0 and stops[0]["cumulative_time_s"] == 0
            assert sum(s["leg_distance_m"] for s in stops) == pytest.approx(route["total_distance_m"])
            assert stops[-1]["cumulative_time_s"] == pytest.approx(route["total_time_s"])
            assert route["rerouted_geometry"] is None  # no accidents, nothing rerouted


def test_multiple_accidents_are_echoed_and_flag_rerouted_legs():
    edges = client.get("/cities/indiranagar_bengaluru/edges").json()
    first = client.post("/jobs/from-nodes", json=_NODES_PAYLOAD).json()["job_id"]
    free = _wait_done(first)
    # Block several real road segments that the no-accident routes actually drive.
    by_coords = {
        frozenset([(round(e["from_lat"], 6), round(e["from_lon"], 6)), (round(e["to_lat"], 6), round(e["to_lon"], 6))]): e
        for e in edges
    }
    geometry = free["ortools"]["routes"][0]["geometry"]
    blocked = []
    for a, b in zip(geometry, geometry[1:]):
        edge = by_coords.get(frozenset([tuple(a), tuple(b)]))
        if edge and edge not in blocked:
            blocked.append(edge)
        if len(blocked) == 6:
            break
    assert len(blocked) >= 2

    payload = {**_NODES_PAYLOAD, "accident_edges": [
        {"from_node_id": e["from_node_id"], "to_node_id": e["to_node_id"]} for e in blocked
    ]}
    result = _wait_done(client.post("/jobs/from-nodes", json=payload).json()["job_id"])

    assert result["accident_edges"] == payload["accident_edges"]
    for algo in ("ortools", "qpso"):
        for route in result[algo]["routes"]:
            assert route["rerouted_geometry"] is not None
    assert any(route["rerouted_geometry"] for route in result["ortools"]["routes"])
