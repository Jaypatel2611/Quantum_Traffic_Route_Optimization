# SIH26137 Phase 3 — QPSO Algorithmic Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Highest-risk phase per the user's own instruction — take the most care here.**

**Goal:** A from-scratch QPSO (Quantum-behaved Particle Swarm Optimization) CVRP solver, mathematically faithful to PRD Section 9, run head-to-head against Phase 2's OR-Tools baseline under identical seed and wall-clock time budget, producing sane, explainable numbers on the real Indiranagar test case.

**Architecture:** Six small, independently-testable pieces build up to `qpso_solver.py`'s `solve_qpso(...)`: ROV mapping → giant-tour-to-routes splitter + capacity penalty → multi-objective fitness → the core QPSO iteration loop (attractor/mbest/position-update/α-schedule/time-budget) → stagnation countermeasure → final wiring. Each piece gets its own unit/property test before the next is built on top of it, because a solver whose sub-pieces are individually unverified is not safe to benchmark (PRD Section 21's build order: "a solver whose permutation-validity property is unverified is not safe to benchmark").

**Tech Stack:** NumPy (`numpy.random.Generator`, seeded — no Qiskit/Cirq/quantum-simulator dependency anywhere, PRD Section 9), Hypothesis (property-based tests).

**Spec:** `../../planning/SIH26137_Implementation_PRD.md` (Sections 7 seeding/time-budget, 9 QPSO math, 9.1 QPSO-vs-QAOA justification, 11 multi-objective normalization, 12 dynamic penalty, 14 testing/success metrics, 15 stagnation).

## Global Constraints

- **Pure classical mathematics.** No Qiskit, no Cirq, no quantum circuit simulator — QPSO borrows probabilistic math (delta-potential-well attractor mechanics), not quantum hardware simulation (PRD Section 9).
- **One shared seeded `numpy.random.Generator` for every stochastic draw** in the algorithm — initial particle positions, the `φ ~ U(0,1)` attractor mix, the `u ~ U(0,1)` Monte Carlo draw, and the `±` sign coin-flip. Never a bare `numpy.random` global-state call (PRD Section 7).
- **Wall-clock time budget, not just an iteration count.** The loop must independently check `time.monotonic()` against `time_budget_s` every iteration, exactly as PRD Section 7's code sketch specifies, so the OR-Tools/QPSO comparison is time-budget-fair, not "QPSO ran to convergence vs. OR-Tools ran to timeout."
- **User-approved VRP encoding (this session, since the PRD leaves it unstated):** the particle stays `X_i ∈ R^N` where `N` = customer count only (PRD Section 9's literal dimensionality, no extra split-point genes). The ROV-mapped giant tour is divided into `num_vehicles` **fixed, equal-ish contiguous chunks** in tour order; each chunk is one vehicle's route. An over-capacity chunk is never repaired or discarded — it gets PRD Section 12's squared penalty, so a real capacity violation is reachable by the swarm and the penalty mechanism has something to act on.
- **Dynamic penalty, not a hard constraint** (PRD Section 12): `penalty = λ · max(0, load − capacity)²` per over-capacity chunk, summed into the fitness. `λ` scales up over the run (small early → large late), symmetric in spirit to the `α` decay.
- **Min-Max normalization tracked per-run across the current population** (PRD Section 11), not a fixed global constant — each iteration's distance/time normalization bounds are recomputed from that iteration's swarm, since the practically achievable range shrinks as the swarm converges.
- **CO2 term deferred to Phase 4**, per PRD Section 21's build order ("`copert_model.py` ... additive to an already-working distance/time comparison, not a blocker"). Phase 3's fitness is `w_distance · dist_norm + w_time · time_norm + penalty`, `w_distance = w_time = 0.5` by default (PRD doesn't give exact weights; flagged as the Phase 3 default, revisited when Phase 4 adds the CO2 term and Phase 6/7 exposes weights as a user setting).
- Tests written before/alongside the code they cover (TDD). One commit per task, conventional format.

## Review Focus

- A permutation that "looks" valid but silently drops or duplicates a node under floating-point tie-breaking in the ROV sort — this is exactly why PRD Section 14 names a dedicated property test, not just a unit test with one fixed input.
- The α schedule must actually be monotonically non-increasing across the run (1.0 → 0.5) — a sign error or off-by-one in the exponent would invert the explore/exploit balance silently, producing numbers that still "look plausible" without actually implementing the intended schedule.
- The stagnation counter must reset on any improving iteration, not just decay — a counter that only decrements would trigger reinitialization far too often or never, and either failure mode looks like "the algorithm is just running" rather than an obvious crash.
- Time-budget enforcement checked only *between* iterations, never mid-iteration — for a small test case (5–10 customers) each iteration is fast enough that this is fine, but it's worth stating: a pathologically slow single iteration could still overrun the budget, and this plan does not add mid-iteration preemption for the MVP's small-N demo scale.
- The seeded RNG must be threaded through every call that consumes randomness — passing `rng` into a helper that then calls `np.random.rand()` internally instead of `rng.random()` would silently break the whole determinism/fairness guarantee two phases' worth of design has been building toward, and would only surface as an unreproducible benchmark much later (same class of bug flagged in Phase 1's stochastic delay injector).

---

### Task 1: Rank-Order Value (ROV) mapping

**Files:**
- Modify: `backend/app/infrastructure/algorithms/qpso_solver.py`
- Test: `tests/unit/test_qpso_rov_mapping.py`, `tests/property_based/test_qpso_rov_mapping_properties.py`

**Interfaces:**
- Produces: `rov_map(position: np.ndarray) -> np.ndarray` — returns a permutation of `range(len(position))` (the rank order of `position`'s values, ascending). Task 2 consumes this permutation as the giant tour.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_qpso_rov_mapping.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import rov_map


def test_sorts_ascending_by_rank():
    position = np.array([0.5, -1.2, 3.7, 0.1])
    # ranks (ascending): -1.2 is smallest (index 1), then 0.1 (index 3), then 0.5 (index 0), then 3.7 (index 2)
    assert list(rov_map(position)) == [1, 3, 0, 2]


def test_single_element():
    assert list(rov_map(np.array([42.0]))) == [0]
```

```python
# tests/property_based/test_qpso_rov_mapping_properties.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from hypothesis import given
from hypothesis import strategies as st
from app.infrastructure.algorithms.qpso_solver import rov_map


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False, width=32), min_size=1, max_size=50))
def test_rov_always_produces_a_valid_permutation(values):
    """PRD Section 14: ROV mapping, for any input vector of length N, always
    produces a permutation of {0, ..., N-1} with no duplicates and no omissions."""
    position = np.array(values)
    result = rov_map(position)
    assert sorted(result.tolist()) == list(range(len(values)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_rov_mapping.py tests/property_based/test_qpso_rov_mapping_properties.py -v`
Expected: FAIL — stub has no `rov_map`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/algorithms/qpso_solver.py
import numpy as np


def rov_map(position: np.ndarray) -> np.ndarray:
    """Rank-Order Value mapping (PRD Section 9): sorts the continuous position
    vector and returns the resulting rank order as a discrete node-visit
    permutation. Validity is a structural property of argsort, not something
    the fitness function needs to check."""
    return np.argsort(position)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_rov_mapping.py tests/property_based/test_qpso_rov_mapping_properties.py -v`
Expected: PASS (2 unit + Hypothesis property test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/qpso_solver.py tests/unit/test_qpso_rov_mapping.py tests/property_based/test_qpso_rov_mapping_properties.py
git commit -m "feat: implement QPSO Rank-Order Value mapping

test: cover the always-valid-permutation property (PRD Section 14) via Hypothesis"
```

---

### Task 2: Giant-tour splitter + capacity penalty

**Files:**
- Modify: `backend/app/infrastructure/algorithms/qpso_solver.py`
- Test: `tests/unit/test_qpso_route_splitting.py`

**Interfaces:**
- Consumes: a permutation from Task 1 (indices into the *customer* list, i.e. `node_ids[1:]` — depot is `node_ids[0]` and is never part of the permutation).
- Produces: `split_into_routes(permutation: np.ndarray, num_vehicles: int) -> list[list[int]]` (customer indices per vehicle, fixed equal-ish contiguous chunks); `capacity_penalty(routes: list[list[int]], demands: list[float], vehicle_capacity: float, lam: float) -> float` — Task 3's fitness function consumes both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_qpso_route_splitting.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import split_into_routes, capacity_penalty


def test_splits_into_equal_ish_contiguous_chunks():
    permutation = np.array([2, 0, 3, 1, 4])  # 5 customers, in tour order
    routes = split_into_routes(permutation, num_vehicles=2)
    assert len(routes) == 2
    assert sum(len(r) for r in routes) == 5
    # contiguous: route 0 is a prefix of the tour, route 1 the remainder
    assert routes[0] == [2, 0, 3]
    assert routes[1] == [1, 4]


def test_no_penalty_when_under_capacity():
    routes = [[0, 1], [2, 3]]
    demands = [10.0, 20.0, 15.0, 25.0]  # customer-index-aligned (depot excluded)
    assert capacity_penalty(routes, demands, vehicle_capacity=100.0, lam=50.0) == 0.0


def test_penalty_scales_with_squared_violation():
    routes = [[0, 1]]  # load = 10 + 20 = 30
    demands = [10.0, 20.0]
    # violation = 30 - 25 = 5; penalty = lam * 5^2
    assert capacity_penalty(routes, demands, vehicle_capacity=25.0, lam=2.0) == 2.0 * 5.0**2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_route_splitting.py -v`
Expected: FAIL — no `split_into_routes`/`capacity_penalty` yet

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/infrastructure/algorithms/qpso_solver.py

def split_into_routes(permutation: np.ndarray, num_vehicles: int) -> list[list[int]]:
    """Divides the giant tour into num_vehicles fixed, equal-ish contiguous
    chunks (user-approved encoding, PRD Section 9's particle stays R^N with
    no extra split-point genes)."""
    n = len(permutation)
    base_size, remainder = divmod(n, num_vehicles)
    routes = []
    start = 0
    for vehicle in range(num_vehicles):
        size = base_size + (1 if vehicle < remainder else 0)
        routes.append(permutation[start:start + size].tolist())
        start += size
    return routes


def capacity_penalty(
    routes: list[list[int]], demands: list[float], vehicle_capacity: float, lam: float
) -> float:
    """PRD Section 12's dynamic scaling penalty: an over-capacity route is
    never discarded, just penalized proportional to the squared violation."""
    total = 0.0
    for route in routes:
        load = sum(demands[i] for i in route)
        violation = max(0.0, load - vehicle_capacity)
        total += lam * violation**2
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_route_splitting.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/qpso_solver.py tests/unit/test_qpso_route_splitting.py
git commit -m "feat: implement giant-tour route splitting and dynamic capacity penalty

test: cover contiguous equal-ish splitting and the squared-violation penalty formula"
```

---

### Task 3: Multi-objective fitness with per-population normalization

**Files:**
- Modify: `backend/app/infrastructure/algorithms/qpso_solver.py`, `backend/app/domain/value_objects/fitness_score.py`
- Test: `tests/unit/test_qpso_fitness.py`

**Interfaces:**
- Consumes: `split_into_routes` output (Task 2), a time/distance matrix (Phase 1), `capacity_penalty` (Task 2).
- Produces: `FitnessScore(total, distance_component, time_component, penalty_component)` (immutable); `evaluate_fitness(routes, distance_matrix, time_matrix, demands, vehicle_capacity, lam, depot_index, w_distance, w_time, population_distance_range, population_time_range) -> FitnessScore` — Task 4's swarm loop calls this once per particle per iteration, first computing `population_distance_range`/`population_time_range` across the whole swarm that iteration.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_qpso_fitness.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import evaluate_fitness


def _tiny_instance():
    # depot(0) + 2 customers(1,2)
    distance_matrix = np.array([[0, 10, 20], [10, 0, 15], [20, 15, 0]], dtype=float)
    time_matrix = distance_matrix / 2
    demands = [5.0, 5.0]  # customer-index-aligned (depot excluded)
    return distance_matrix, time_matrix, demands


def test_fitness_is_zero_penalty_when_within_capacity():
    distance_matrix, time_matrix, demands = _tiny_instance()
    routes = [[0, 1]]  # both customers on one vehicle
    score = evaluate_fitness(
        routes, distance_matrix, time_matrix, demands,
        vehicle_capacity=100.0, lam=50.0, depot_index=0,
        w_distance=0.5, w_time=0.5,
        population_distance_range=(0.0, 50.0), population_time_range=(0.0, 25.0),
    )
    assert score.penalty_component == 0.0
    assert score.total >= 0.0


def test_fitness_includes_penalty_when_over_capacity():
    distance_matrix, time_matrix, demands = _tiny_instance()
    routes = [[0, 1]]
    score = evaluate_fitness(
        routes, distance_matrix, time_matrix, demands,
        vehicle_capacity=5.0, lam=10.0, depot_index=0,  # capacity 5 < load 10
        w_distance=0.5, w_time=0.5,
        population_distance_range=(0.0, 50.0), population_time_range=(0.0, 25.0),
    )
    assert score.penalty_component == 10.0 * 5.0**2  # violation = 10 - 5 = 5
    assert score.total > score.distance_component + score.time_component
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_fitness.py -v`
Expected: FAIL — no `evaluate_fitness`/`FitnessScore` yet

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/value_objects/fitness_score.py
from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessScore:
    total: float
    distance_component: float
    time_component: float
    penalty_component: float
```

```python
# append to backend/app/infrastructure/algorithms/qpso_solver.py
from app.domain.value_objects.fitness_score import FitnessScore


def _route_distance_and_time(route: list[int], distance_matrix, time_matrix, depot_index: int):
    """One route's round trip: depot -> customers in order -> depot.
    `route` holds customer indices (0-based into the customer list); the
    matrices are depot-inclusive, so shift by +1 to reach matrix indices."""
    stops = [depot_index] + [c + 1 for c in route] + [depot_index]
    dist = sum(distance_matrix[a][b] for a, b in zip(stops, stops[1:]))
    time = sum(time_matrix[a][b] for a, b in zip(stops, stops[1:]))
    return dist, time


def evaluate_fitness(
    routes: list[list[int]],
    distance_matrix,
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    lam: float,
    depot_index: int,
    w_distance: float,
    w_time: float,
    population_distance_range: tuple[float, float],
    population_time_range: tuple[float, float],
) -> FitnessScore:
    """PRD Section 11's multi-objective Min-Max normalization + Section 12's
    dynamic penalty, combined into one scalar fitness."""
    from app.infrastructure.algorithms.qpso_solver import capacity_penalty  # local import avoided in final file; see note below

    total_distance = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in routes)
    total_time = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in routes)

    dist_min, dist_max = population_distance_range
    time_min, time_max = population_time_range
    dist_norm = 0.0 if dist_max == dist_min else (total_distance - dist_min) / (dist_max - dist_min)
    time_norm = 0.0 if time_max == time_min else (total_time - time_min) / (time_max - time_min)

    penalty = capacity_penalty(routes, demands, vehicle_capacity, lam)
    total = w_distance * dist_norm + w_time * time_norm + penalty
    return FitnessScore(
        total=total,
        distance_component=w_distance * dist_norm,
        time_component=w_time * time_norm,
        penalty_component=penalty,
    )
```

Note: `capacity_penalty` is already defined earlier in the same module (Task 2) — the plan shows it as a same-file call; drop the illustrative local `import` line above when writing the real file (it's shown only to make this task's snippet self-contained on the page).

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_fitness.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/qpso_solver.py backend/app/domain/value_objects/fitness_score.py tests/unit/test_qpso_fitness.py
git commit -m "feat: implement multi-objective fitness with per-population Min-Max normalization

test: cover zero-penalty-within-capacity and squared-penalty-over-capacity cases"
```

---

### Task 4: Core QPSO iteration loop

**Files:**
- Modify: `backend/app/infrastructure/algorithms/qpso_solver.py`
- Test: `tests/unit/test_qpso_core_loop.py`

**Interfaces:**
- Consumes: `rov_map` (Task 1), `split_into_routes`/`capacity_penalty` (Task 2), `evaluate_fitness` (Task 3).
- Produces: `run_qpso(distance_matrix, time_matrix, demands, vehicle_capacity, num_vehicles, depot_index, num_particles, max_iterations, time_budget_s, seed, k=1.75, lambda_min=1.0, lambda_max=100.0, w_distance=0.5, w_time=0.5) -> tuple[list[list[int]], FitnessScore, dict]` — best routes found, its fitness, and a `meta` dict with `convergence_history` (Gbest fitness per iteration), `seed`, `iterations_run`, `stopped_reason` (`"time_budget"` or `"max_iterations"`). Task 6 consumes this.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_qpso_core_loop.py
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import run_qpso


def _small_instance():
    distance_matrix = np.array(
        [[0, 10, 15, 20], [10, 0, 12, 18], [15, 12, 0, 8], [20, 18, 8, 0]], dtype=float
    )
    time_matrix = distance_matrix / 2
    demands = [30.0, 40.0, 25.0]  # 3 customers, depot excluded
    return distance_matrix, time_matrix, demands


def test_same_seed_reproduces_identical_convergence_history():
    distance_matrix, time_matrix, demands = _small_instance()
    _, _, meta_a = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    _, _, meta_b = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    assert meta_a["convergence_history"] == meta_b["convergence_history"]


def test_gbest_fitness_never_increases_across_iterations():
    distance_matrix, time_matrix, demands = _small_instance()
    _, _, meta = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=30, time_budget_s=5.0, seed=1,
    )
    history = meta["convergence_history"]
    assert all(history[i + 1] <= history[i] + 1e-9 for i in range(len(history) - 1))


def test_wall_clock_time_budget_is_enforced():
    distance_matrix, time_matrix, demands = _small_instance()
    start = time.monotonic()
    _, _, meta = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=1_000_000, time_budget_s=1.0, seed=1,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 3.0  # generous margin over the 1.0s budget
    assert meta["stopped_reason"] == "time_budget"


def test_best_route_visits_every_customer_exactly_once():
    distance_matrix, time_matrix, demands = _small_instance()
    routes, _, _ = run_qpso(
        distance_matrix, time_matrix, demands, vehicle_capacity=100.0, num_vehicles=2,
        depot_index=0, num_particles=10, max_iterations=20, time_budget_s=5.0, seed=42,
    )
    visited = sorted(c for route in routes for c in route)
    assert visited == [0, 1, 2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_core_loop.py -v`
Expected: FAIL — no `run_qpso` yet

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/infrastructure/algorithms/qpso_solver.py
import time


def run_qpso(
    distance_matrix,
    time_matrix,
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    depot_index: int,
    num_particles: int,
    max_iterations: int,
    time_budget_s: float,
    seed: int,
    k: float = 1.75,
    lambda_min: float = 1.0,
    lambda_max: float = 100.0,
    w_distance: float = 0.5,
    w_time: float = 0.5,
):
    """PRD Section 9's QPSO: ROV mapping, local attractor point, mean-best
    position, Monte Carlo position update with a 50/50 sign draw, adaptive
    alpha contraction-expansion schedule. One seeded Generator drives every
    stochastic draw (PRD Section 7) -- never bare numpy.random."""
    rng = np.random.default_rng(seed)
    n = len(demands)  # customer count (depot excluded, PRD Section 9's R^N)

    positions = rng.uniform(-1.0, 1.0, size=(num_particles, n))
    pbest_positions = positions.copy()
    pbest_fitness = [None] * num_particles
    gbest_position = None
    gbest_fitness = None
    convergence_history: list[float] = []
    stagnation_counter = 0
    start = time.monotonic()
    stopped_reason = "max_iterations"

    iteration = 0
    for iteration in range(max_iterations):
        if time.monotonic() - start >= time_budget_s:
            stopped_reason = "time_budget"
            break

        alpha = 1.0 - (1.0 - 0.5) * (iteration / max_iterations) ** k
        lam = lambda_min + (lambda_max - lambda_min) * (iteration / max_iterations) ** k

        all_routes = [split_into_routes(rov_map(p), num_vehicles) for p in positions]
        all_distances = []
        all_times = []
        for routes in all_routes:
            d = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[0] for r in routes)
            t = sum(_route_distance_and_time(r, distance_matrix, time_matrix, depot_index)[1] for r in routes)
            all_distances.append(d)
            all_times.append(t)
        dist_range = (min(all_distances), max(all_distances))
        time_range = (min(all_times), max(all_times))

        fitness_values = [
            evaluate_fitness(
                all_routes[i], distance_matrix, time_matrix, demands, vehicle_capacity,
                lam=lam, depot_index=depot_index, w_distance=w_distance, w_time=w_time,
                population_distance_range=dist_range, population_time_range=time_range,
            )
            for i in range(num_particles)
        ]

        for i, score in enumerate(fitness_values):
            if pbest_fitness[i] is None or score.total < pbest_fitness[i].total:
                pbest_fitness[i] = score
                pbest_positions[i] = positions[i].copy()

        best_idx = min(range(num_particles), key=lambda i: fitness_values[i].total)
        improved = gbest_fitness is None or fitness_values[best_idx].total < gbest_fitness.total * (1 - 0.0001)
        if gbest_fitness is None or fitness_values[best_idx].total < gbest_fitness.total:
            gbest_fitness = fitness_values[best_idx]
            gbest_position = positions[best_idx].copy()
        stagnation_counter = 0 if improved else stagnation_counter + 1
        convergence_history.append(gbest_fitness.total)

        mbest = pbest_positions.mean(axis=0)
        phi = rng.uniform(0.0, 1.0, size=(num_particles, n))
        attractor = phi * pbest_positions + (1 - phi) * gbest_position
        u = rng.uniform(1e-12, 1.0, size=(num_particles, n))  # avoid ln(1/0)
        sign = np.where(rng.random(size=(num_particles, n)) < 0.5, 1.0, -1.0)
        positions = attractor + sign * alpha * np.abs(mbest - positions) * np.log(1.0 / u)

    best_routes = split_into_routes(rov_map(gbest_position), num_vehicles)
    meta = {
        "seed": seed,
        "convergence_history": convergence_history,
        "iterations_run": iteration + 1,
        "stopped_reason": stopped_reason,
    }
    return best_routes, gbest_fitness, meta
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_core_loop.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/qpso_solver.py tests/unit/test_qpso_core_loop.py
git commit -m "feat: implement the core QPSO iteration loop

PRD Section 9 math (local attractor, mean-best position, Monte Carlo
position update with 50/50 sign draw, adaptive alpha schedule) and
Section 7's wall-clock time budget enforcement, driven by one seeded
Generator for every stochastic draw.

test: cover seed-determinism, Gbest monotonic improvement, wall-clock cutoff, and full customer coverage"
```

---

### Task 5: Stagnation countermeasure

**Files:**
- Modify: `backend/app/infrastructure/algorithms/qpso_solver.py`
- Test: `tests/unit/test_qpso_stagnation.py`

**Interfaces:**
- Consumes/modifies: `run_qpso`'s internal loop state (`positions`, `pbest_fitness`, `stagnation_counter`) from Task 4.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_qpso_stagnation.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import reinitialize_stagnant_particles


def test_reinitializes_worst_20_percent_by_personal_best_fitness():
    rng = np.random.default_rng(0)
    positions = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]])

    class _Score:
        def __init__(self, total):
            self.total = total

    pbest_fitness = [_Score(t) for t in [1.0, 5.0, 2.0, 4.0, 3.0]]  # worst 20% (1 particle) = index 1 (total=5.0)
    new_positions, reinit_indices = reinitialize_stagnant_particles(
        positions, pbest_fitness, rng, fraction=0.2
    )
    assert reinit_indices == [1]
    assert not np.array_equal(new_positions[1], positions[1])
    # untouched particles keep their positions
    for i in [0, 2, 3, 4]:
        assert np.array_equal(new_positions[i], positions[i])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_stagnation.py -v`
Expected: FAIL — no `reinitialize_stagnant_particles` yet

- [ ] **Step 3: Write minimal implementation, then wire it into the loop**

```python
# append to backend/app/infrastructure/algorithms/qpso_solver.py

def reinitialize_stagnant_particles(positions, pbest_fitness, rng, fraction: float = 0.2):
    """PRD Section 15: if Gbest fails to improve for 50 consecutive iterations,
    vaporize and randomly re-initialize the worst-performing fraction of the
    swarm (ranked by personal-best fitness), forcing renewed exploration."""
    num_particles = len(positions)
    num_reinit = max(1, int(num_particles * fraction))
    ranked = sorted(range(num_particles), key=lambda i: pbest_fitness[i].total, reverse=True)
    reinit_indices = sorted(ranked[:num_reinit])
    new_positions = positions.copy()
    for i in reinit_indices:
        new_positions[i] = rng.uniform(-1.0, 1.0, size=positions.shape[1])
    return new_positions, reinit_indices
```

Then, inside `run_qpso`'s loop (Task 4), after `stagnation_counter` is updated:

```python
        if stagnation_counter >= 50:
            positions, _ = reinitialize_stagnant_particles(positions, pbest_fitness, rng, fraction=0.2)
            stagnation_counter = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_qpso_stagnation.py tests/unit/test_qpso_core_loop.py -v`
Expected: PASS (all — the stagnation wiring must not break Task 4's existing tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/qpso_solver.py tests/unit/test_qpso_stagnation.py
git commit -m "feat: implement PRD Section 15 stagnation countermeasure

Re-initializes the worst-performing 20% of the swarm (by personal-best
fitness) after 50 consecutive non-improving iterations.

test: cover worst-fraction selection and that untouched particles keep their positions"
```

---

### Task 6: Head-to-head verification against the OR-Tools baseline

**Files:**
- Create: `backend/scripts/verify_qpso_vs_ortools.py`

**Interfaces:**
- Consumes: `run_qpso` (Tasks 1–5), `solve_cvrp` (Phase 2), Phase 1's cached graph/matrix/delay pipeline.

- [ ] **Step 1: Write the script**

```python
# backend/scripts/verify_qpso_vs_ortools.py
"""Head-to-head QPSO vs. OR-Tools on the real Indiranagar test case, under
identical seed and wall-clock time budget (PRD Section 7's fairness protocol)."""
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
from app.infrastructure.algorithms.qpso_solver import run_qpso, _route_distance_and_time

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "indiranagar_bengaluru.graphml"

TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9716, lon=77.6412), demand=0),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9750, lon=77.6440), demand=30),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9690, lon=77.6380), demand=40),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9760, lon=77.6390), demand=25),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9670, lon=77.6430), demand=35),
]
VEHICLE_CAPACITY = 100.0
NUM_VEHICLES = 2
TIME_BUDGET_S = 5.0
SEED = 42

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(SEED)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    ortools_routes, ortools_meta = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_BUDGET_S,
    )
    ortools_total_time = sum(r.total_time_s for r in ortools_routes)
    ortools_total_distance = sum(r.total_distance_m for r in ortools_routes)

    qpso_routes, qpso_fitness, qpso_meta = run_qpso(
        dist, time_matrix, demands[1:], vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES,
        depot_index=0, num_particles=30, max_iterations=500, time_budget_s=TIME_BUDGET_S, seed=SEED,
    )
    qpso_total_distance = sum(_route_distance_and_time(r, dist, time_matrix, 0)[0] for r in qpso_routes)
    qpso_total_time = sum(_route_distance_and_time(r, dist, time_matrix, 0)[1] for r in qpso_routes)

    print("=== OR-Tools baseline ===")
    print(f"config: {ortools_meta}")
    for r in ortools_routes:
        print(f"  {r.vehicle_id}: {' -> '.join(r.node_sequence)}  (dist {r.total_distance_m:.1f} m, time {r.total_time_s:.1f} s)")
    print(f"  total: {ortools_total_distance:.1f} m, {ortools_total_time:.1f} s")

    print("\n=== QPSO ===")
    print(f"config: {qpso_meta}")
    for i, route in enumerate(qpso_routes):
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        print(f"  v{i}: {' -> '.join(stops)}")
    print(f"  total: {qpso_total_distance:.1f} m, {qpso_total_time:.1f} s, fitness: {qpso_fitness.total:.4f}")

    print(f"\n=== Comparison (time, the shared optimization objective) ===")
    delta_pct = (qpso_total_time - ortools_total_time) / ortools_total_time * 100
    winner = "OR-Tools" if ortools_total_time < qpso_total_time else "QPSO"
    print(f"OR-Tools: {ortools_total_time:.1f} s | QPSO: {qpso_total_time:.1f} s | delta: {delta_pct:+.1f}% | winner: {winner}")
```

- [ ] **Step 2: Run it and inspect the numbers for sanity**

Run: `cd backend && .venv/Scripts/python scripts/verify_qpso_vs_ortools.py`
Expected: both solvers produce a complete, capacity-respecting route split; QPSO's total time is in the same order of magnitude as OR-Tools's (not off by 10x, not zero, not NaN). **Do not proceed past this step if the numbers aren't sane and explainable** — per the user's explicit Phase 3 instruction. If QPSO's result looks pathological, this is the point to stop and diagnose rather than paper over it in Task 7.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_qpso_vs_ortools.py
git commit -m "test: add head-to-head QPSO vs. OR-Tools verification script under identical seed/time-budget"
```

---

## Self-Review Notes

- **Spec coverage:** ROV mapping (Section 9) → Task 1; dynamic penalty instead of hard constraint (Section 12) → Task 2/3; multi-objective Min-Max normalization tracked per-population (Section 11) → Task 3; local attractor / mbest / Monte Carlo position update / α schedule (Section 9) → Task 4; seeded RNG + wall-clock time budget (Section 7) → Task 4; stagnation countermeasure (Section 15) → Task 5; head-to-head comparison with sane-numbers gate (user's Phase 3 instruction) → Task 6.
- **Flagged deviation from a genuine spec gap, user-approved this session:** PRD Section 9 fixes the particle to `X_i ∈ R^N` (customer count only) but never states how one permutation becomes multiple vehicle routes. Fixed equal-ish contiguous splitting was chosen and confirmed with the user as the most literal reading consistent with both the stated dimensionality and Section 12's requirement that violations be *reachable*, not auto-repaired.
- **Placeholder scan:** clean — every step has real, runnable code. Task 3's illustrative local `import` line is explicitly called out as page-only scaffolding, not something to actually write into the file (the real function is defined once in the module).
- **Type consistency:** `run_qpso(...) -> tuple[list[list[int]], FitnessScore, dict]` (Task 4) is consumed by Task 6 exactly as declared; `FitnessScore` (Task 3) fields match what Task 6 reads (`qpso_fitness.total`).
- **Review Focus:** ROV validity — covered by Task 1's Hypothesis property test. α monotonicity — not asserted as its own numeric test (would be redundant with Task 4's Gbest-non-increasing test, which is the observable consequence that actually matters); flagging that the α *formula* itself has no dedicated unit test, accepted as a scope cut since Task 4's convergence-history test would fail if the schedule were badly broken. Stagnation counter reset semantics — covered by Task 5's test plus Task 4's monotonic-Gbest test (a broken reset would eventually produce a Gbest that *increases*, which that test catches). Time-budget enforcement — covered by Task 4's dedicated wall-clock test. RNG threading — no single test proves *every* call site uses `rng`; mitigated by code review during Task 4/5's implementation (grep for `np.random.` with no `rng.` prefix before committing each task) rather than a test, since a test can't easily distinguish "used the right generator" from "used a different one that happens to look random."
