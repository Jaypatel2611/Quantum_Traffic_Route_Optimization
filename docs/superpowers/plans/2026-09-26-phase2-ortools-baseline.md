# SIH26137 Phase 2 — Classical Baseline (OR-Tools) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working single-depot, homogeneous-fleet CVRP solver using Google OR-Tools, configured exactly per PRD Section 9.2, run against Phase 1's real distance/time matrices, producing routes Phase 3's QPSO will be benchmarked against.

**Architecture:** One infrastructure module (`or_tools_baseline.py`) plus two domain entities (`Vehicle`, `Route`) that give solver input/output typed shape. No orchestrator/API wiring yet — proven via unit tests and a standalone script, same pattern as Phase 1 (PRD Section 21's build order: "Implement `or_tools_baseline.py` first... gives the team an immediate working route-comparison baseline").

**Tech Stack:** `ortools.constraint_solver.pywrapcp`, `ortools.constraint_solver.routing_enums_pb2`.

**Spec:** `../../planning/SIH26137_Implementation_PRD.md` (Sections 7 seeding/fairness, 9.2 OR-Tools config, 12 precision-recall trade-off context, 21 build order).

## Global Constraints

- `first_solution_strategy = PATH_CHEAPEST_ARC`, `local_search_metaheuristic = GUIDED_LOCAL_SEARCH`, hard wall-clock `time_limit` — exactly PRD Section 9.2's three configuration points, not a subset.
- **Confirmed by direct inspection, not assumed:** the installed `ortools==9.15.6755`'s `RoutingSearchParameters` proto has no `random_seed` field (full field list checked). Per PRD Section 7, this must be surfaced as an explicit, logged known limitation — never silently ignored — so the fairness claim two phases from now is honest about what seed-parity actually covers (time-budget parity, not RNG-state parity, on the OR-Tools side).
- Single depot, homogeneous fleet (PRD Section 0/6) — no multi-depot, no heterogeneous capacities.
- `Vehicle.fuel_type` scaffolded now even though unused until Phase 4/V2 (PRD Section 6: "already scaffolded in the MVP data model").
- OR-Tools arc costs must be integers; time-matrix values (possibly fractional seconds after Phase 1's stochastic delay injection) are rounded to the nearest second for the routing callback — a standard OR-Tools constraint, not a spec gap.
- Tests written before/alongside the code they cover (TDD). One commit per task, conventional format.

## Review Focus

- A vehicle capacity too small for any single customer's demand would make the CVRP provably infeasible — OR-Tools returns `None` from `SolveWithParameters` in that case, and the code must raise a clear error, not silently return an empty/wrong route.
- The optimization objective must be stated explicitly: this plan optimizes on **time** (the post-stochastic-delay matrix), not distance, because Phase 3's QPSO fairness comparison and the demo's latency framing are both time-based (PRD doesn't pin this down explicitly for OR-Tools; distance is still reported for the user's "show me total distance/time" ask, computed post-hoc from the route, not part of the solver's own cost function).
- Depot demand must be exactly 0 — a depot with nonzero demand would double-count capacity usage on every route that returns to it.
- An unused vehicle (empty route, PATH_CHEAPEST_ARC found a feasible answer using fewer vehicles than offered) must not appear in the output as a spurious zero-length "route."
- The known-seed-limitation must be a visible field in the function's return value, not just a code comment — Phase 3's benchmarking report (PRD Section 14's "every reported number must be reproducible from this log alone") needs to log it.

---

### Task 1: Domain entities — `Vehicle`, `Route`

**Files:**
- Modify: `backend/app/domain/entities/vehicle.py`, `backend/app/domain/entities/route.py`
- Test: `tests/unit/test_vehicle.py`, `tests/unit/test_route.py`

**Interfaces:**
- Produces: `Vehicle(id: str, capacity: float, fuel_type: str = "diesel")` (raises `ValueError` if `capacity <= 0`); `Route(vehicle_id: str, node_sequence: list[str], total_distance_m: float, total_time_s: float)` — Task 2's solver constructs these from its solution.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_vehicle.py
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
```

```python
# tests/unit/test_route.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.domain.entities.route import Route


def test_route_constructs():
    r = Route(vehicle_id="v1", node_sequence=["depot", "n1", "n2", "depot"], total_distance_m=1200.0, total_time_s=180.0)
    assert r.node_sequence[0] == r.node_sequence[-1] == "depot"
    assert r.total_distance_m == 1200.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_vehicle.py tests/unit/test_route.py -v`
Expected: FAIL — `ImportError` (stub modules export nothing yet)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/entities/vehicle.py
from dataclasses import dataclass


@dataclass
class Vehicle:
    id: str
    capacity: float
    fuel_type: str = "diesel"

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {self.capacity}")
```

```python
# backend/app/domain/entities/route.py
from dataclasses import dataclass


@dataclass
class Route:
    vehicle_id: str
    node_sequence: list[str]
    total_distance_m: float
    total_time_s: float
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_vehicle.py tests/unit/test_route.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/entities/vehicle.py backend/app/domain/entities/route.py tests/unit/test_vehicle.py tests/unit/test_route.py
git commit -m "feat: implement Vehicle and Route domain entities"
```

---

### Task 2: OR-Tools CVRP baseline solver (`or_tools_baseline.py`)

**Files:**
- Install: `ortools` into `backend/.venv`, re-freeze `backend/requirements.txt`
- Modify: `backend/app/infrastructure/algorithms/or_tools_baseline.py`
- Test: `tests/unit/test_or_tools_baseline.py`

**Interfaces:**
- Consumes: `time_matrix: np.ndarray`, `distance_matrix: np.ndarray` (Phase 1), `node_ids: list[str]`, `demands: list[float]` (index-aligned with the matrices; `demands[depot_index]` must be `0`), `vehicle_capacity: float`, `num_vehicles: int`, `depot_index: int = 0`, `time_limit_s: float = 5.0`.
- Produces: `solve_cvrp(...) -> tuple[list[Route], dict]` — the `dict` carries `{"seed_configurable": False, "time_limit_s": ..., "first_solution_strategy": "PATH_CHEAPEST_ARC", "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH"}`. Task 3 consumes both.

- [ ] **Step 1: Install and re-freeze**

```bash
cd backend
.venv/Scripts/python -m pip install ortools
.venv/Scripts/python -m pip freeze > requirements.txt
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/test_or_tools_baseline.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
import pytest
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp


def _small_instance():
    # depot + 3 customers, small enough to solve instantly
    time_matrix = np.array(
        [
            [0, 10, 15, 20],
            [10, 0, 12, 18],
            [15, 12, 0, 8],
            [20, 18, 8, 0],
        ],
        dtype=float,
    )
    distance_matrix = time_matrix * 50  # arbitrary meters-per-second-ish scaling for the test
    node_ids = ["depot", "n1", "n2", "n3"]
    demands = [0, 30, 40, 25]
    return time_matrix, distance_matrix, node_ids, demands


def test_all_customers_visited_exactly_once():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, meta = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    visited = [node for route in routes for node in route.node_sequence if node != "depot"]
    assert sorted(visited) == ["n1", "n2", "n3"]


def test_every_route_starts_and_ends_at_depot():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, _ = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    for route in routes:
        assert route.node_sequence[0] == "depot"
        assert route.node_sequence[-1] == "depot"


def test_capacity_constraint_is_respected():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    routes, _ = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=50.0, num_vehicles=2, time_limit_s=5.0,
    )
    demand_by_id = dict(zip(node_ids, demands))
    for route in routes:
        route_demand = sum(demand_by_id[n] for n in route.node_sequence if n != "depot")
        assert route_demand <= 50.0


def test_known_seed_limitation_is_reported_not_silenced():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    _, meta = solve_cvrp(
        time_matrix, distance_matrix, node_ids, demands,
        vehicle_capacity=100.0, num_vehicles=2, time_limit_s=5.0,
    )
    assert meta["seed_configurable"] is False
    assert meta["first_solution_strategy"] == "PATH_CHEAPEST_ARC"
    assert meta["local_search_metaheuristic"] == "GUIDED_LOCAL_SEARCH"


def test_infeasible_capacity_raises_clear_error():
    time_matrix, distance_matrix, node_ids, demands = _small_instance()
    with pytest.raises(RuntimeError, match="feasible"):
        solve_cvrp(
            time_matrix, distance_matrix, node_ids, demands,
            vehicle_capacity=10.0, num_vehicles=1, time_limit_s=2.0,
        )
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_or_tools_baseline.py -v`
Expected: FAIL — stub has no `solve_cvrp`

- [ ] **Step 4: Write minimal implementation**

```python
# backend/app/infrastructure/algorithms/or_tools_baseline.py
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.domain.entities.route import Route

# Confirmed by direct inspection of ortools==9.15.6755's RoutingSearchParameters
# proto field list: there is no random_seed field. Per PRD Section 7, this is a
# known limitation to surface explicitly, not a silent gap — the fairness
# comparison with QPSO (Phase 3) is time-budget-matched, not RNG-state-matched,
# on the OR-Tools side.
SEED_CONFIGURABLE = False


def solve_cvrp(
    time_matrix,
    distance_matrix,
    node_ids: list[str],
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    depot_index: int = 0,
    time_limit_s: float = 5.0,
) -> tuple[list[Route], dict]:
    """CVRP via OR-Tools, optimizing on time (PRD Section 9.2): PATH_CHEAPEST_ARC
    first-solution strategy, GUIDED_LOCAL_SEARCH metaheuristic, hard time limit."""
    n = len(node_ids)
    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(round(time_matrix[from_node][to_node]))

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [int(vehicle_capacity)] * num_vehicles, True, "Capacity"
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(int(round(time_limit_s)))

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        raise RuntimeError(
            f"OR-Tools found no feasible solution within time_limit_s={time_limit_s} "
            f"(vehicle_capacity={vehicle_capacity}, num_vehicles={num_vehicles}) — "
            "check that capacity * num_vehicles covers total demand."
        )

    routes: list[Route] = []
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        sequence = [node_ids[manager.IndexToNode(index)]]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            sequence.append(node_ids[manager.IndexToNode(index)])
        if len(sequence) <= 2:  # depot -> depot only: this vehicle was unused
            continue

        total_distance_m = sum(
            distance_matrix[node_ids.index(a)][node_ids.index(b)]
            for a, b in zip(sequence, sequence[1:])
        )
        total_time_s = sum(
            time_matrix[node_ids.index(a)][node_ids.index(b)]
            for a, b in zip(sequence, sequence[1:])
        )
        routes.append(
            Route(
                vehicle_id=f"v{vehicle_id}",
                node_sequence=sequence,
                total_distance_m=float(total_distance_m),
                total_time_s=float(total_time_s),
            )
        )

    meta = {
        "seed_configurable": SEED_CONFIGURABLE,
        "time_limit_s": time_limit_s,
        "first_solution_strategy": "PATH_CHEAPEST_ARC",
        "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
    }
    return routes, meta
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_or_tools_baseline.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/infrastructure/algorithms/or_tools_baseline.py backend/requirements.txt tests/unit/test_or_tools_baseline.py
git commit -m "feat: implement OR-Tools CVRP baseline solver

PRD Section 9.2 config (PATH_CHEAPEST_ARC, GUIDED_LOCAL_SEARCH, hard
time limit). Confirmed by direct inspection: ortools==9.15.6755's
RoutingSearchParameters has no random_seed field -- reported as an
explicit known limitation in the solver's return metadata, not silenced.

test: cover visit-completeness, depot start/end, capacity constraint, the known-limitation report, and infeasible-capacity error handling"
```

---

### Task 3: End-to-end verification against the real Indiranagar graph

**Files:**
- Create: `backend/scripts/verify_or_tools_baseline.py`

**Interfaces:**
- Consumes: `load_cached_graph`, `build_distance_time_matrix`, `inject_stochastic_delay` (Phase 1), `solve_cvrp` (Task 2).

- [ ] **Step 1: Write the script**

```python
# backend/scripts/verify_or_tools_baseline.py
"""Standalone, offline verification of the OR-Tools baseline against the
real cached Indiranagar graph and Phase 1's 5-node test case."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"

# Same 5 points as Phase 1's verification script, now with demands assigned.
# depot demand 0; n1..n4 demands chosen so total (130) needs 2 vehicles at
# capacity 100 each -- exercises the capacity constraint for real, not trivially.
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]
VEHICLE_CAPACITY = 100.0
NUM_VEHICLES = 2
TIME_LIMIT_S = 5.0  # PRD Section 7's cited example hard timeout

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(42)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    routes, meta = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_LIMIT_S,
    )

    print(f"Solver config: {meta}")
    print(f"\n{len(routes)} route(s) found:")
    for route in routes:
        print(f"  {route.vehicle_id}: {' -> '.join(route.node_sequence)}")
        print(f"    distance: {route.total_distance_m:.1f} m, time: {route.total_time_s:.1f} s")

    total_distance = sum(r.total_distance_m for r in routes)
    total_time = sum(r.total_time_s for r in routes)
    print(f"\nTotal across all routes: {total_distance:.1f} m, {total_time:.1f} s")
```

- [ ] **Step 2: Run it and capture the output**

Run: `cd backend && .venv/Scripts/python scripts/verify_or_tools_baseline.py`
Expected: prints solver config (including `seed_configurable: False`), each route with its sequence and distance/time, and the total — this is the "show me the output route and total distance/time" deliverable.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_or_tools_baseline.py
git commit -m "test: add standalone OR-Tools baseline verification script against the real Indiranagar graph"
```

---

## Self-Review Notes

- **Spec coverage:** PATH_CHEAPEST_ARC/GUIDED_LOCAL_SEARCH/hard time limit (Section 9.2) → Task 2; seed-limitation logging requirement (Section 7) → Task 2's `meta` dict and its dedicated test; single-depot/homogeneous-fleet CVRP with capacity (Section 0/6) → Task 2; `Vehicle.fuel_type` scaffolding (Section 6) → Task 1; the route/distance/time printout the user explicitly asked for → Task 3.
- **Placeholder scan:** clean — every step has real, runnable code.
- **Type consistency:** `solve_cvrp(...) -> tuple[list[Route], dict]` (Task 2) is consumed by Task 3 exactly as declared; `Route` (Task 1) fields match what Task 2 constructs and what Task 3 prints.
- **Deliberately deferred, stated not silenced:** `application/interfaces/solver_port.py` stays a stub, same reasoning as Phase 1's `geospatial_repository_port.py` — no caller until Phase 5's `OptimizationOrchestrator` needs the abstraction.
- **Review Focus:** infeasible-capacity error — covered by Task 2's dedicated test. Objective-metric ambiguity (time vs. distance) — stated explicitly above and in code, both reported. Depot demand — enforced by convention (`demands[0] == 0` in the test fixture and the verification script) rather than a runtime assertion, since Phase 6/7's Pydantic schema is the real boundary validator for user-submitted demand data (consistent with Phase 1's self-review on where validation responsibility lives). Unused-vehicle filtering — covered by Task 2's route-extraction logic and implicitly exercised by the capacity test (which forces 2 vehicles to actually both be used). Visible seed-limitation reporting — covered by Task 2's dedicated test, not just a comment.
