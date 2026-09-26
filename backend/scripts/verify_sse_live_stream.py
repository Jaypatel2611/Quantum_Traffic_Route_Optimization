"""Starts the real app, kicks off a job on the real Indiranagar test case,
and prints each raw SSE event as it arrives live -- proving the streaming
mechanism works end to end, not just in isolated unit tests. A chart is
Phase 6's job; this proves the data feed a chart would consume is real
and live."""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np
import uvicorn

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.main import app

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]

if __name__ == "__main__":
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8123, log_level="warning"), daemon=True
    )
    server_thread.start()
    time.sleep(1.0)

    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(42)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    payload = {
        "time_matrix": time_matrix.tolist(), "distance_matrix": dist.tolist(),
        "node_ids": [n.id for n in TEST_NODES], "demands": [n.demand for n in TEST_NODES],
        "vehicle_capacity": 100.0, "num_vehicles": 2, "depot_index": 0,
        "seed": 42, "time_budget_s": 8.0,
    }
    with httpx.Client(base_url="http://127.0.0.1:8123") as client:
        job_id = client.post("/jobs", json=payload).json()["job_id"]
        print(f"Job {job_id} started -- streaming live events:\n")
        with client.stream("GET", f"/jobs/{job_id}/stream", timeout=15.0) as response:
            for line in response.iter_lines():
                if line:
                    print(f"  [{time.strftime('%H:%M:%S')}] {line}")
