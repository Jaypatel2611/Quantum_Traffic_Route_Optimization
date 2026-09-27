"""One-off verification: does the 60-node demo scenario produce a real,
non-zero CO2/time delta between OR-Tools and QPSO (unlike the 5-node
reference scenario, where both solvers find the identical route)?
Requires a running backend on 127.0.0.1:8000 (`uvicorn app.main:app`).

Usage: cd backend && .venv/Scripts/python scripts/verify_bigger_scenario.py
"""
import csv
import time
from pathlib import Path

import httpx

CSV_PATH = Path(__file__).resolve().parents[2] / "docs" / "demo_scenarios" / "indiranagar_60.csv"

with open(CSV_PATH) as f:
    nodes = [
        {"id": row["node_id"], "lat": float(row["lat"]), "lon": float(row["lon"]), "demand": float(row["demand"])}
        for row in csv.DictReader(f)
    ]

payload = {
    "city_id": "indiranagar_bengaluru",
    "nodes": nodes,
    "vehicle_capacity": 150.0,
    "num_vehicles": 8,
    "seed": 42,
    "time_budget_s": 15.0,
}

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
    job_id = client.post("/jobs/from-nodes", json=payload).json()["job_id"]
    print(f"job {job_id} started, {len(nodes)} nodes, waiting for result...")

    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{job_id}/result").json()
        if result["status"] == "done":
            break
        if result["status"] == "error":
            raise SystemExit(f"job errored: {result}")
        time.sleep(1.0)
    else:
        raise SystemExit("job never completed within 60s")

    print(f"OR-Tools: {len(result['ortools']['routes'])} routes, "
          f"{result['ortools']['total_co2_kg']:.3f} kg CO2, {result['ortools']['total_time_s']:.1f}s")
    print(f"QPSO:     {len(result['qpso']['routes'])} routes, "
          f"{result['qpso']['total_co2_kg']:.3f} kg CO2, {result['qpso']['total_time_s']:.1f}s")
    print(f"Green impact: {result['green_impact']}")
