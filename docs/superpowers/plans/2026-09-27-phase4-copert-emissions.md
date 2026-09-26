# SIH26137 Phase 4 — Ecological Metrics (COPERT) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A COPERT-based CO2 emissions model, applied to Phase 2's OR-Tools and Phase 3's QPSO routes on the same real Indiranagar test case, reporting the emissions delta between them as the primary demoable "Egreen Quanta" sustainability number.

**Architecture:** One infrastructure module (`copert_model.py`) plus one domain value object (`CO2EmissionProfile`). No orchestrator/API wiring yet, same pattern as Phases 1–3 — proven via unit tests and a standalone comparison script (PRD Section 21 build order: COPERT "last among backend pieces — additive to an already-working distance/time comparison, not a blocker").

**Tech Stack:** Pure Python/NumPy, no new dependencies.

**Spec:** `../../../SIH26137_Implementation_PRD.md` (Section 13 COPERT integration, Section 14 testing table, Section 6 `Vehicle.fuel_type`).

## Global Constraints

- **Real, cited emission-factor source, verified via web search across three independent queries converging on the same academic citation, not invented from memory:** EMEP/EEA Guidebook-derived formula for diesel passenger cars <2.5t, valid speed range 10–130 km/h: `CO2(v) = 286 − 4.07·v + 0.0271·v²` g/km. This deviates from PRD Section 13's own illustrative rational form `(a + b·v + c·v²)/v` — the real published formula is a direct quadratic in `v`, not divided by `v`. Using the real, verifiable curve over a forced-fit approximation of the PRD's paraphrase is the more defensible choice, per the user's explicit sign-off this session.
- **User-decided methodology (this session, resolving a genuine PRD tension):** PRD Section 13 asks for COPERT's *shape* rescaled by an *IPCC per-liter-fuel* magnitude proxy, specifically because COPERT's own published numbers are European-fleet-calibrated. Doing that rescale would need an assumed India-specific fuel-economy figure (L/100km) with no confidently sourced number — a second, less-verifiable guess stacked on the first. **Decision: use the real COPERT formula's magnitude as-is**, explicitly flagged as European-fleet-calibrated (not India-specific), rather than compounding it with an unsourced conversion. ARAI/CPCB India-specific coefficients are flagged as a V2 dependency, not available within this prototype's timeframe.
- **Primary reported metric is the relative % CO2 reduction between the classical (OR-Tools) and QPSO routes**, not the absolute kg figure — per the user's explicit correction. Absolute kg is shown only as secondary, clearly-labeled context.
- **Speed clamped to the formula's validated domain, `[10, 130]` km/h** — extrapolating the quadratic outside the range it was fit/published for is not defensible; clamping is the honest choice, documented as such.
- **Flagged simplification (stated, not silent):** emissions are computed from each route's **average speed** (`total_distance_m / total_time_s`), not true per-edge integration (PRD Section 13's literal wording: "queries `EF(v)` for the average speed of each edge"). Phase 1's distance/time matrices are aggregated point-to-point sums, not retained edge-path sequences — true per-edge fidelity would need reworking `distance_matrix_builder.py` to preserve the path, out of this phase's scope. `# ponytail: route-average-speed approximation, upgrade to per-edge EF(v) integration if distance_matrix_builder starts tracking edge paths.`
- `Vehicle.fuel_type` (already scaffolded, Phase 2) stays `"diesel"` — the only fuel class this formula covers; heterogeneous fuel types are V2 (PRD Section 6).
- Tests written before/alongside the code they cover (TDD). One commit per task, conventional format.

## Review Focus

- A route whose average speed falls below 10 km/h (very plausible after Phase 1's stochastic peak-hour delay injection, which can push travel times well past free-flow) must clamp to the formula's floor, not silently extrapolate into negative-derivative territory the published curve was never validated for.
- Division-by-zero: a route with `total_time_s == 0` (shouldn't occur given Phase 2/3's non-empty routes, but worth a guard) would make average-speed computation blow up.
- The emissions-reduction percentage's sign convention must be unambiguous: positive = QPSO emits less than OR-Tools (an improvement), not the reverse — worth a dedicated test, since a flipped sign would silently invert the sustainability claim on a judge-facing number.
- COPERT's real formula only needs three unit-tested reference points (Section 14: "at least three speed bands") — actually pin all three (idle/low-speed, the curve's true minimum at ~75 km/h, highway) with hand-computed values, not just "some" arbitrary points.
- The European-fleet-calibration caveat must be visible in code (a runnable, checkable thing — a constant/docstring), not only in this plan document, since Phase 6/7's "assumptions modal" and any pitch-deck slide will need to source their disclaimer text from somewhere the code actually says.

---

### Task 1: COPERT CO2 emission-factor model (`copert_model.py`)

**Files:**
- Modify: `backend/app/infrastructure/algorithms/copert_model.py`, `backend/app/domain/value_objects/co2_emission_profile.py`
- Test: `tests/unit/test_copert_model.py`

**Interfaces:**
- Produces: `EMISSION_FACTOR_SOURCE` (a string constant naming the source and its European-fleet-calibration caveat, for Phase 6/7's assumptions modal to read); `emission_factor_g_per_km(speed_kmh: float) -> float` (clamps to `[10, 130]`); `CO2EmissionProfile(total_kg: float, average_speed_kmh: float, fuel_type: str = "diesel")` (immutable) — Task 2 consumes both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_copert_model.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.infrastructure.algorithms.copert_model import emission_factor_g_per_km, EMISSION_FACTOR_SOURCE


def test_source_is_documented_not_silent():
    assert "European" in EMISSION_FACTOR_SOURCE
    assert "EMEP" in EMISSION_FACTOR_SOURCE or "COPERT" in EMISSION_FACTOR_SOURCE


@pytest.mark.parametrize(
    "speed_kmh,expected_g_per_km",
    [
        (10.0, 248.01),   # low-speed/idle-adjacent band
        (75.09, 133.18726951),  # the curve's true minimum (v = 4.07 / (2*0.0271))
        (130.0, 214.89),  # highway band
    ],
)
def test_known_reference_values(speed_kmh, expected_g_per_km):
    """PRD Section 14: unit tests against known reference values for at
    least three speed bands (idle, cruise, highway) -- hand-computed
    directly from the sourced formula's own coefficients."""
    assert emission_factor_g_per_km(speed_kmh) == pytest.approx(expected_g_per_km, abs=1e-4)


def test_clamps_below_validated_range():
    # formula validated for [10, 130]; a speed of 2 km/h clamps to 10's value
    assert emission_factor_g_per_km(2.0) == emission_factor_g_per_km(10.0)


def test_clamps_above_validated_range():
    assert emission_factor_g_per_km(200.0) == emission_factor_g_per_km(130.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_copert_model.py -v`
Expected: FAIL — stub has no `emission_factor_g_per_km`/`EMISSION_FACTOR_SOURCE`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/algorithms/copert_model.py

# Source: EMEP/EEA Air Pollutant Emission Inventory Guidebook-derived COPERT
# formula for diesel passenger cars < 2.5t, valid speed range 10-130 km/h.
# Verified via three independent web searches converging on the same
# citation (2026-09-27) -- not recalled from memory, per the project's
# rule against unsourced figures on a judge-facing sustainability number.
#
# CAVEAT, stated explicitly (not silent): these coefficients are
# CALIBRATED ON THE EUROPEAN VEHICLE FLEET, not Indian vehicles.
# India-specific ARAI/CPCB coefficients were not located within this
# prototype's timeframe (flagged as a V2 dependency) -- the PRD's own
# Section 13 research finding. User-decided (2026-09-27): use this real,
# verifiable curve as-is rather than compound it with a second, unsourced
# India-specific fuel-economy assumption. The primary reported metric is
# therefore the RELATIVE % CO2 reduction between routes under this one
# standardized methodology, not the absolute kg figure.
EMISSION_FACTOR_SOURCE = (
    "EMEP/EEA Guidebook COPERT formula, diesel passenger car <2.5t, "
    "European-fleet-calibrated (ARAI/CPCB India-specific coefficients: V2 dependency)"
)

_A, _B, _C = 286.0, -4.07, 0.0271
_MIN_VALID_SPEED_KMH = 10.0
_MAX_VALID_SPEED_KMH = 130.0


def emission_factor_g_per_km(speed_kmh: float) -> float:
    """CO2 g/km as a function of average speed. Clamped to the formula's
    validated range -- extrapolating a fitted quadratic outside where it
    was published for is not defensible."""
    v = min(max(speed_kmh, _MIN_VALID_SPEED_KMH), _MAX_VALID_SPEED_KMH)
    return _A + _B * v + _C * v**2
```

```python
# backend/app/domain/value_objects/co2_emission_profile.py
from dataclasses import dataclass


@dataclass(frozen=True)
class CO2EmissionProfile:
    total_kg: float
    average_speed_kmh: float
    fuel_type: str = "diesel"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_copert_model.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/copert_model.py backend/app/domain/value_objects/co2_emission_profile.py tests/unit/test_copert_model.py
git commit -m "feat: implement COPERT CO2 emission-factor model

Real EMEP/EEA-derived formula (diesel passenger car <2.5t, 10-130
km/h), verified via web search, not recalled from memory. Explicitly
flagged as European-fleet-calibrated -- ARAI/CPCB India-specific
coefficients are a stated V2 dependency, not silently assumed.

test: cover the documented source string and three hand-computed reference speed bands (PRD Section 14)"
```

---

### Task 2: Route/solution emissions aggregation + reduction percentage

**Files:**
- Modify: `backend/app/infrastructure/algorithms/copert_model.py`
- Test: `tests/unit/test_copert_emissions_aggregation.py`

**Interfaces:**
- Consumes: `Route` (Phase 2's `total_distance_m`/`total_time_s`), `emission_factor_g_per_km` (Task 1).
- Produces: `route_emissions(route: Route) -> CO2EmissionProfile`; `total_emissions_kg(routes: list[Route] | list[list[int]], ...) -> float`; `co2_reduction_percent(baseline_kg: float, optimized_kg: float) -> float` — Task 3 consumes all three.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_copert_emissions_aggregation.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.route import Route
from app.infrastructure.algorithms.copert_model import (
    route_emissions, total_emissions_kg, co2_reduction_percent,
)


def test_route_emissions_uses_average_speed():
    # 10 km at a steady pace taking 600s (10 minutes) -> 60 km/h average
    route = Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)
    profile = route_emissions(route)
    assert profile.average_speed_kmh == pytest.approx(60.0)
    # EF(60) = 286 - 4.07*60 + 0.0271*3600 = 286 - 244.2 + 97.56 = 139.36 g/km, over 10 km
    assert profile.total_kg == pytest.approx(139.36 * 10 / 1000, abs=1e-4)


def test_total_emissions_sums_across_routes():
    r1 = Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)
    r2 = Route(vehicle_id="v1", node_sequence=["depot", "n2", "depot"], total_distance_m=5_000.0, total_time_s=300.0)
    total = total_emissions_kg([r1, r2])
    assert total == pytest.approx(route_emissions(r1).total_kg + route_emissions(r2).total_kg)


def test_reduction_percent_positive_means_optimized_emits_less():
    """Sign convention: positive = improvement (QPSO/optimized route emits
    less than the baseline) -- a flipped sign would invert the sustainability
    claim silently on a judge-facing number."""
    assert co2_reduction_percent(baseline_kg=100.0, optimized_kg=80.0) == pytest.approx(20.0)


def test_reduction_percent_negative_means_optimized_emits_more():
    assert co2_reduction_percent(baseline_kg=100.0, optimized_kg=120.0) == pytest.approx(-20.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_copert_emissions_aggregation.py -v`
Expected: FAIL — no `route_emissions`/`total_emissions_kg`/`co2_reduction_percent` yet

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/infrastructure/algorithms/copert_model.py
from app.domain.value_objects.co2_emission_profile import CO2EmissionProfile


def route_emissions(route) -> CO2EmissionProfile:
    """ponytail: route-average-speed approximation (not per-edge EF(v)
    integration) -- Phase 1's matrices are aggregated point-to-point sums,
    not retained edge paths. Upgrade path: per-edge integration if
    distance_matrix_builder starts tracking the path."""
    distance_km = route.total_distance_m / 1000
    average_speed_kmh = distance_km / (route.total_time_s / 3600)
    total_kg = emission_factor_g_per_km(average_speed_kmh) * distance_km / 1000
    return CO2EmissionProfile(total_kg=total_kg, average_speed_kmh=average_speed_kmh)


def total_emissions_kg(routes) -> float:
    return sum(route_emissions(r).total_kg for r in routes)


def co2_reduction_percent(baseline_kg: float, optimized_kg: float) -> float:
    """Positive = optimized route emits less than baseline (an improvement)."""
    return (baseline_kg - optimized_kg) / baseline_kg * 100
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_copert_emissions_aggregation.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/algorithms/copert_model.py tests/unit/test_copert_emissions_aggregation.py
git commit -m "feat: implement route/solution emissions aggregation and CO2 reduction percentage

test: cover average-speed derivation, multi-route summation, and the improvement-sign convention"
```

---

### Task 3: Emissions delta between Phase 2 and Phase 3 routes (end-to-end)

**Files:**
- Create: `backend/scripts/verify_emissions_delta.py`

**Interfaces:**
- Consumes: `solve_cvrp` (Phase 2), `run_qpso` (Phase 3), `total_emissions_kg`/`co2_reduction_percent` (Task 2), Phase 1's cached graph/matrix/delay pipeline.

- [ ] **Step 1: Write the script**

```python
# backend/scripts/verify_emissions_delta.py
"""Emissions delta between the OR-Tools baseline and QPSO routes on the
real Indiranagar test case, under identical seed/time-budget -- the
user's explicit Phase 4 ask."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.entities.route import Route
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay
from app.infrastructure.algorithms.or_tools_baseline import solve_cvrp
from app.infrastructure.algorithms.qpso_solver import run_qpso, _route_distance_and_time
from app.infrastructure.algorithms.copert_model import (
    total_emissions_kg, co2_reduction_percent, EMISSION_FACTOR_SOURCE,
)

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
    print(f"Emission factor source: {EMISSION_FACTOR_SOURCE}\n")

    graph = load_cached_graph(CACHE_PATH)
    dist, base_time = build_distance_time_matrix(graph, TEST_NODES)
    rng = np.random.default_rng(SEED)
    time_matrix = inject_stochastic_delay(base_time, rng, hour_of_day=8.0)

    node_ids = [n.id for n in TEST_NODES]
    demands = [n.demand for n in TEST_NODES]

    ortools_routes, _ = solve_cvrp(
        time_matrix, dist, node_ids, demands,
        vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES, time_limit_s=TIME_BUDGET_S,
    )
    ortools_co2_kg = total_emissions_kg(ortools_routes)

    qpso_routes, _, _ = run_qpso(
        dist, time_matrix, demands[1:], vehicle_capacity=VEHICLE_CAPACITY, num_vehicles=NUM_VEHICLES,
        depot_index=0, num_particles=30, max_iterations=500, time_budget_s=TIME_BUDGET_S, seed=SEED,
    )
    # QPSO's routes are customer-index lists; wrap as Route objects for total_emissions_kg
    qpso_route_objs = []
    for i, route in enumerate(qpso_routes):
        d, t = _route_distance_and_time(route, dist, time_matrix, 0)
        stops = ["depot"] + [node_ids[c + 1] for c in route] + ["depot"]
        qpso_route_objs.append(Route(vehicle_id=f"v{i}", node_sequence=stops, total_distance_m=d, total_time_s=t))
    qpso_co2_kg = total_emissions_kg(qpso_route_objs)

    print(f"OR-Tools baseline CO2: {ortools_co2_kg:.4f} kg")
    print(f"QPSO CO2:              {qpso_co2_kg:.4f} kg")
    reduction = co2_reduction_percent(baseline_kg=ortools_co2_kg, optimized_kg=qpso_co2_kg)
    print(f"\nRelative CO2 reduction (QPSO vs. OR-Tools): {reduction:+.2f}%")
    print("(Primary reported metric per user decision 2026-09-27 -- absolute kg above is secondary,")
    print(" European-fleet-calibrated context, not a precise India-specific figure.)")
```

- [ ] **Step 2: Run it and capture the output**

Run: `cd backend && .venv/Scripts/python scripts/verify_emissions_delta.py`
Expected: prints the emission factor source disclaimer, both routes' absolute CO2 (kg), and the relative % reduction. Given Task 6 of Phase 3 found these two routes to be numerically identical on this tiny 5-node instance, the expected result here is **0.00% delta** — explainable for the same reason (both solvers found the same optimal route split), not a bug. Record this in the explainability log rather than being surprised by it a second time.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_emissions_delta.py
git commit -m "test: add end-to-end emissions delta script between OR-Tools and QPSO routes"
```

---

## Self-Review Notes

- **Spec coverage:** COPERT polynomial CO2 model (Section 13) → Task 1; unit tests against known reference values for 3 speed bands (Section 14) → Task 1; emissions delta between Phase 2/3 routes (user's Phase 4 instruction) → Task 3.
- **Flagged deviations, all user-approved or verified this session:** (1) real EMEP/EEA quadratic formula used instead of PRD's illustrative rational form — more defensible than force-fitting an approximation to an illustrative snippet; (2) COPERT's real magnitude used as-is rather than IPCC-rescaled, to avoid stacking an unsourced India-specific fuel-economy guess — user decision; (3) route-average-speed used instead of per-edge integration — stated ceiling/upgrade path, consistent with Phase 1's data model.
- **Placeholder scan:** clean — every step has real, runnable code.
- **Type consistency:** `route_emissions(route) -> CO2EmissionProfile` (Task 2) matches `CO2EmissionProfile`'s fields from Task 1; `total_emissions_kg`/`co2_reduction_percent` signatures match Task 3's usage exactly.
- **Review Focus:** sub-10km/h clamping — covered by Task 1's dedicated test. Division-by-zero on `total_time_s == 0` — not defended with an explicit guard/test; accepted as a scope cut since Phase 2/3's solvers structurally cannot produce a route with zero total time (every route has at least one non-depot stop with nonzero travel time) — flagging this reasoning here rather than adding a defensive check for a state the upstream solvers can't produce. Sign convention — covered by Task 2's two dedicated tests (both directions). Three reference speed bands — covered exactly, including the curve's true minimum (~75 km/h, not the PRD prose's approximate 40–60 km/h — the real curve's minimum, computed from its own coefficients, not guessed). European-calibration caveat visible in code — `EMISSION_FACTOR_SOURCE` constant, tested directly in Task 1.
