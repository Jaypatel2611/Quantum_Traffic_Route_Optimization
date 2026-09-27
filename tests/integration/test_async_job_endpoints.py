import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_PAYLOAD = {
    "time_matrix": [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]],
    "distance_matrix": [[0, 500, 750, 1000], [500, 0, 600, 900], [750, 600, 0, 400], [1000, 900, 400, 0]],
    "node_ids": ["depot", "n1", "n2", "n3"],
    "demands": [0, 30, 40, 25],
    "vehicle_capacity": 100.0,
    "num_vehicles": 2,
    "depot_index": 0,
    "seed": 42,
    "time_budget_s": 3.0,
}


def test_health_stays_responsive_during_a_concurrent_solver_run():
    """PRD Section 14's named integration test: concurrent solver requests
    must not block the event loop -- /health stays sub-100ms responsive
    throughout a running job."""
    response = client.post("/jobs", json=_PAYLOAD)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    for _ in range(5):
        start = time.monotonic()
        health_response = client.get("/health")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert health_response.status_code == 200
        assert elapsed_ms < 100
        time.sleep(0.3)


def test_stream_endpoint_returns_event_stream_content_type():
    response = client.post("/jobs", json=_PAYLOAD)
    job_id = response.json()["job_id"]
    with client.stream("GET", f"/jobs/{job_id}/stream") as stream_response:
        assert stream_response.headers["content-type"].startswith("text/event-stream")


def test_malformed_matrix_returns_422_not_a_solver_crash():
    """Real Pydantic validation (this endpoint's own former gap, closed
    alongside /jobs/from-nodes's): a matrix that isn't actually a list of
    lists must never reach the solver."""
    payload = {**_PAYLOAD, "time_matrix": "not a matrix"}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_non_positive_num_vehicles_returns_422():
    payload = {**_PAYLOAD, "num_vehicles": 0}
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
