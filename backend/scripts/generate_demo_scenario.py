"""Generates a bigger (default: 60-node) demo scenario CSV, sampled from real
graph nodes in the cached Indiranagar graph, so every generated coordinate is
guaranteed on-road and routable -- avoids the 5-node reference scenario's
"both solvers find the identical route" degenerate case, which reports a
0.00% CO2/time delta everywhere in the UI.

Usage: cd backend && .venv/Scripts/python scripts/generate_demo_scenario.py [num_nodes] [seed]
"""
import csv
import sys
from pathlib import Path

import numpy as np
import osmnx as ox

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "demo_scenarios"


def generate(num_customers: int, seed: int) -> list[dict]:
    graph = ox.load_graphml(str(CACHE_PATH))
    graph_nodes = list(graph.nodes(data=True))
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(graph_nodes), size=num_customers + 1, replace=False)

    rows = []
    for i, idx in enumerate(chosen):
        _, data = graph_nodes[idx]
        is_depot = i == 0
        demand = 0 if is_depot else int(rng.integers(5, 31))
        rows.append({
            "node_id": "depot" if is_depot else f"n{i}",
            "lat": data["y"],
            "lon": data["x"],
            "demand": demand,
        })
    return rows


if __name__ == "__main__":
    num_customers = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    rows = generate(num_customers, seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH = OUT_DIR / f"indiranagar_{num_customers}.csv"
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["node_id", "lat", "lon", "demand"])
        writer.writeheader()
        writer.writerows(rows)

    total_demand = sum(r["demand"] for r in rows)
    print(f"Wrote {len(rows)} nodes ({num_customers} customers + 1 depot) to {OUT_PATH}")
    print(f"Total demand: {total_demand}")
