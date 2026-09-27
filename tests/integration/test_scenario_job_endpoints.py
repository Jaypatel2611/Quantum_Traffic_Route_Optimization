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
