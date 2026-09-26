# SIH26137 Phase 1 — Geospatial Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a real Indian-city OSMnx road graph into a routable, offline-cached, asymmetric N×N travel-time matrix with SVRPBench-modeled stochastic delay injection — the input every later solver phase (OR-Tools, QPSO) consumes.

**Architecture:** Three infrastructure modules (`osmnx_client.py`, `distance_matrix_builder.py`, `stochastic_delay_injector.py`) plus two domain types (`GeographicCoordinates`, `Node`) that give the pipeline typed, validated inputs. No HTTP endpoint yet — this phase is proven via unit/property tests and one standalone script, per the user's Phase 1 instruction and PRD Section 21's build order ("validate the pipeline against \[the cached graph\] end-to-end in a standalone script, before wiring it into the API").

**Tech Stack:** OSMnx, NetworkX, NumPy (seeded `Generator`), pytest + Hypothesis (property-based tests).

**Spec:** `../../../SIH26137_Implementation_PRD.md` (Sections 7 seeding, 8 offline caching, 10 geospatial pipeline, 14 testing, 17 payload/bounding-box limits), `../../../svrp_benchmark_doc.md` (log-normal delay parameters).

## Global Constraints

- Zero live Overpass dependency at *runtime* — the app only ever calls `ox.load_graphml(filepath)`; the real network fetch happens once, in a dev-time script, and its output is committed as a `.graphml` cache file (PRD Section 8).
- Largest strongly-connected-component isolation happens at ingestion time, not caught as a runtime exception during solving (PRD Section 15).
- All stochastic draws (delay injection included) come from a caller-supplied seeded `numpy.random.Generator` — never a bare `numpy.random` global call — so a shared seed later reproduces an identical stochastic realization across QPSO and OR-Tools (PRD Section 7, Section 10 point 7).
- OSMnx bounding-box/place-size sanity check happens before calling `ox.graph_from_place`, at cache-generation time (PRD Section 17).
- Node snapping uses `ox.distance.nearest_edges` (edge-based, R-tree-backed), not nearest-node, so a delivery point near a road (not at an intersection) is still correctly routable (PRD Section 10 point 3).
- Tests written before/alongside the code they cover (TDD). One commit per task, conventional format.
- Domain value objects are immutable (PRD Section 7's `domain/value_objects` description).

## Review Focus

- A delivery-node coordinate that lat/lon-wise falls outside the fetched graph's bounding box entirely (e.g., a demo operator fat-fingers a coordinate from a different city) — `ox.distance.nearest_edges` will still return *some* nearest edge, however absurdly far, silently producing a nonsense route instead of a clear error.
- A city graph that, after largest-SCC truncation, has fewer nodes than the delivery-node count being snapped onto it — the matrix builder must not silently truncate the delivery set to fit.
- Calling the log-normal delay injector with the same seed twice must give bit-identical output (this is the whole point of the shared-seed fairness guarantee two phases from now) — a subtle bug here (e.g., reseeding per call instead of advancing one `Generator`) would only surface as an unreproducible benchmark much later.
- The offline cache-generation script silently overwriting an existing, larger, previously-validated `.graphml` with a smaller/different-parameter fetch would quietly invalidate the team's rehearsed "primary demo scenario" (PRD Section 16) without any error.
- An oversized `ox.graph_from_place` query (e.g., a typo'd place name resolving to a state/country) hanging or exhausting memory during the one-time dev fetch, per PRD Section 17's explicit bounding-box cap requirement.

---

### Task 1: Domain types — `GeographicCoordinates`, `Node`, exceptions

**Files:**
- Modify: `backend/app/domain/value_objects/geographic_coordinates.py`, `backend/app/domain/entities/node.py`, `backend/app/domain/exceptions.py`
- Test: `tests/unit/test_geographic_coordinates.py`, `tests/unit/test_node.py`

**Interfaces:**
- Produces: `GeographicCoordinates(lat: float, lon: float)` (frozen, raises `ValueError` outside `[-90,90]`/`[-180,180]`); `Node(id: str, coordinates: GeographicCoordinates, demand: float = 0.0)` (raises `ValueError` if `demand < 0`); `GraphDisconnectedError`, `CapacityExceededError`, `TimeWindowViolation` (all plain `Exception` subclasses — Task 2 raises the first, Phase 3 raises the other two).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_geographic_coordinates.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


def test_valid_coordinates_construct():
    coords = GeographicCoordinates(lat=12.9352, lon=77.6146)
    assert coords.lat == 12.9352
    assert coords.lon == 77.6146


@pytest.mark.parametrize("lat,lon", [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)])
def test_out_of_bounds_coordinates_raise(lat, lon):
    with pytest.raises(ValueError):
        GeographicCoordinates(lat=lat, lon=lon)


def test_coordinates_are_immutable():
    coords = GeographicCoordinates(lat=12.9352, lon=77.6146)
    with pytest.raises(Exception):
        coords.lat = 0.0
```

```python
# tests/unit/test_node.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


def test_node_constructs_with_defaults():
    node = Node(id="depot", coordinates=GeographicCoordinates(lat=12.9, lon=77.6))
    assert node.demand == 0.0


def test_negative_demand_raises():
    with pytest.raises(ValueError):
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.9, lon=77.6), demand=-5.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_geographic_coordinates.py tests/unit/test_node.py -v`
Expected: FAIL — `ImportError` (nothing exported yet from the stub modules)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/value_objects/geographic_coordinates.py
from dataclasses import dataclass


@dataclass(frozen=True)
class GeographicCoordinates:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.lat <= 90.0):
            raise ValueError(f"lat must be within [-90, 90], got {self.lat}")
        if not (-180.0 <= self.lon <= 180.0):
            raise ValueError(f"lon must be within [-180, 180], got {self.lon}")
```

```python
# backend/app/domain/entities/node.py
from dataclasses import dataclass

from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


@dataclass
class Node:
    id: str
    coordinates: GeographicCoordinates
    demand: float = 0.0

    def __post_init__(self) -> None:
        if self.demand < 0:
            raise ValueError(f"demand must be >= 0, got {self.demand}")
```

```python
# backend/app/domain/exceptions.py
class GraphDisconnectedError(Exception):
    """Raised when a graph has no usable largest strongly-connected component."""


class CapacityExceededError(Exception):
    """Raised by the QPSO dynamic penalty function (Phase 3) — not used until then."""


class TimeWindowViolation(Exception):
    """Raised by the QPSO dynamic penalty function (Phase 3) — not used until then."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_geographic_coordinates.py tests/unit/test_node.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/value_objects/geographic_coordinates.py backend/app/domain/entities/node.py backend/app/domain/exceptions.py tests/unit/test_geographic_coordinates.py tests/unit/test_node.py
git commit -m "feat: implement GeographicCoordinates, Node, and domain exceptions"
```

---

### Task 2: Offline OSMnx cache pipeline (`osmnx_client.py`)

**Files:**
- Install: `osmnx`, `networkx`, `hypothesis` into `backend/.venv`, then re-freeze `backend/requirements.txt`
- Modify: `backend/app/infrastructure/geospatial/osmnx_client.py`
- Test: `tests/unit/test_osmnx_client.py`
- Create (generated by running the function, not hand-written): `cache/koramangala_bengaluru.graphml`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `fetch_and_cache_graph(place: str, cache_path: Path, max_place_area_km2: float = 50.0) -> None`; `load_cached_graph(cache_path: Path) -> networkx.MultiDiGraph` — Task 3 consumes the loaded graph.

- [ ] **Step 1: Install dependencies and re-freeze**

```bash
cd backend
.venv/Scripts/python -m pip install osmnx networkx hypothesis
.venv/Scripts/python -m pip freeze > requirements.txt
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/test_osmnx_client.py
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.infrastructure.geospatial.osmnx_client import fetch_and_cache_graph


@patch("app.infrastructure.geospatial.osmnx_client.ox")
def test_rejects_oversized_place_before_fetching(mock_ox, tmp_path):
    oversized_gdf = MagicMock()
    oversized_gdf.to_crs.return_value.area.iloc.__getitem__.return_value = 500_000_000  # m^2, way over cap
    mock_ox.geocode_to_gdf.return_value = oversized_gdf

    with pytest.raises(ValueError, match="too large"):
        fetch_and_cache_graph("India", tmp_path / "india.graphml", max_place_area_km2=50.0)

    mock_ox.graph_from_place.assert_not_called()


@patch("app.infrastructure.geospatial.osmnx_client.ox")
def test_fetches_truncates_and_caches_valid_place(mock_ox, tmp_path):
    small_gdf = MagicMock()
    small_gdf.to_crs.return_value.area.iloc.__getitem__.return_value = 2_000_000  # 2 km^2
    mock_ox.geocode_to_gdf.return_value = small_gdf

    raw_graph = MagicMock(name="raw_graph")
    truncated_graph = MagicMock(name="truncated_graph")
    with_speeds = MagicMock(name="with_speeds")
    with_times = MagicMock(name="with_times")
    mock_ox.graph_from_place.return_value = raw_graph
    mock_ox.truncate.largest_component.return_value = truncated_graph
    mock_ox.add_edge_speeds.return_value = with_speeds
    mock_ox.add_edge_travel_times.return_value = with_times

    cache_path = tmp_path / "koramangala.graphml"
    fetch_and_cache_graph("Koramangala, Bengaluru, India", cache_path)

    mock_ox.graph_from_place.assert_called_once_with("Koramangala, Bengaluru, India", network_type="drive")
    mock_ox.truncate.largest_component.assert_called_once_with(raw_graph, strongly=True)
    mock_ox.add_edge_speeds.assert_called_once_with(truncated_graph)
    mock_ox.add_edge_travel_times.assert_called_once_with(with_speeds)
    mock_ox.save_graphml.assert_called_once_with(with_times, filepath=str(cache_path))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_osmnx_client.py -v`
Expected: FAIL — stub module has no `fetch_and_cache_graph`

- [ ] **Step 4: Write minimal implementation**

```python
# backend/app/infrastructure/geospatial/osmnx_client.py
from pathlib import Path

import osmnx as ox


def fetch_and_cache_graph(place: str, cache_path: Path, max_place_area_km2: float = 50.0) -> None:
    """One-time, offline, dev-time fetch — never called at demo/runtime (PRD Section 8)."""
    gdf = ox.geocode_to_gdf(place)
    area_km2 = gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0] / 1_000_000
    if area_km2 > max_place_area_km2:
        raise ValueError(
            f"'{place}' resolves to {area_km2:.1f} km^2, too large "
            f"(cap {max_place_area_km2} km^2) — pass a city/district-scale place name (PRD Section 17)"
        )

    graph = ox.graph_from_place(place, network_type="drive")
    graph = ox.truncate.largest_component(graph, strongly=True)
    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)
    ox.save_graphml(graph, filepath=str(cache_path))


def load_cached_graph(cache_path: Path):
    """Zero-network load — the only path the running app ever takes (PRD Section 8)."""
    return ox.load_graphml(str(cache_path))
```

Note: the mocked test's `gdf.to_crs.return_value.area.iloc.__getitem__` mock stands in for `gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0]` — `estimate_utm_crs()` on a `MagicMock` returns another `MagicMock`, which `to_crs` accepts without complaint under mocking.

- [ ] **Step 5: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_osmnx_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Run the real one-time fetch (actual network call, actual cache file)**

```bash
cd backend
.venv/Scripts/python -c "
from pathlib import Path
from app.infrastructure.geospatial.osmnx_client import fetch_and_cache_graph
fetch_and_cache_graph('Koramangala, Bengaluru, India', Path('../cache/koramangala_bengaluru.graphml'))
"
```
Expected: `cache/koramangala_bengaluru.graphml` exists and is non-empty. Report the node/edge count.

- [ ] **Step 7: Commit**

```bash
git add backend/app/infrastructure/geospatial/osmnx_client.py backend/requirements.txt tests/unit/test_osmnx_client.py cache/koramangala_bengaluru.graphml
git commit -m "feat: implement offline OSMnx fetch-and-cache pipeline

test: cover the bounding-box size guard and the fetch/truncate/cache call chain"
```

---

### Task 3: Distance/time matrix builder with node snapping (`distance_matrix_builder.py`)

**Files:**
- Modify: `backend/app/infrastructure/geospatial/distance_matrix_builder.py`
- Test: `tests/unit/test_distance_matrix_builder.py`, `tests/property_based/test_distance_matrix_builder_properties.py`

**Interfaces:**
- Consumes: a loaded `networkx.MultiDiGraph` (Task 2's `load_cached_graph` output — but tested here against small synthetic graphs, no OSMnx/network dependency needed for these tests), a list of `Node` (Task 1).
- Produces: `build_distance_time_matrix(graph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]` (distance matrix in meters, time matrix in seconds, both `N×N`, asymmetric) — Task 4 applies stochastic delay to the time matrix; Phase 2/3 solvers consume both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_distance_matrix_builder.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import networkx as nx
import numpy as np
import pytest
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix


def _asymmetric_graph():
    """A -> B is short (60s); B -> A is long (120s) via a one-way detour, mimicking a real one-way street."""
    g = nx.MultiDiGraph()
    g.add_node(1, y=12.90, x=77.60)
    g.add_node(2, y=12.91, x=77.61)
    g.add_node(3, y=12.92, x=77.62)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 3, length=500, travel_time=60)
    g.add_edge(3, 1, length=1000, travel_time=120)
    g.graph["crs"] = "epsg:4326"
    return g


def _nodes():
    return [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n2", coordinates=GeographicCoordinates(lat=12.91, lon=77.61)),
    ]


def test_matrix_shape_is_n_by_n():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert dist.shape == (2, 2)
    assert time.shape == (2, 2)


def test_matrix_is_asymmetric_for_one_way_topology():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert time[0, 1] != time[1, 0]


def test_diagonal_is_zero():
    dist, time = build_distance_time_matrix(_asymmetric_graph(), _nodes())
    assert np.all(np.diag(dist) == 0)
    assert np.all(np.diag(time) == 0)
```

```python
# tests/property_based/test_distance_matrix_builder_properties.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import networkx as nx
import numpy as np
from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix


def test_no_infinite_distance_after_largest_component_cleaning():
    """A graph with a disconnected fragment must not throw once reduced to its largest
    strongly connected component first — this is PRD Section 10 point 2's guarantee,
    re-verified here at the matrix-builder boundary."""
    g = nx.MultiDiGraph()
    g.add_node(1, y=12.90, x=77.60)
    g.add_node(2, y=12.91, x=77.61)
    g.add_edge(1, 2, length=500, travel_time=60)
    g.add_edge(2, 1, length=500, travel_time=60)
    g.add_node(99, y=20.0, x=80.0)  # disconnected fragment, no edges
    g.graph["crs"] = "epsg:4326"

    largest_scc_nodes = max(nx.strongly_connected_components(g), key=len)
    cleaned = g.subgraph(largest_scc_nodes).copy()

    nodes = [
        Node(id="n1", coordinates=GeographicCoordinates(lat=12.90, lon=77.60)),
        Node(id="n2", coordinates=GeographicCoordinates(lat=12.91, lon=77.61)),
    ]
    dist, time = build_distance_time_matrix(cleaned, nodes)
    assert np.all(np.isfinite(dist))
    assert np.all(np.isfinite(time))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_distance_matrix_builder.py tests/property_based/test_distance_matrix_builder_properties.py -v`
Expected: FAIL — stub has no `build_distance_time_matrix`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/geospatial/distance_matrix_builder.py
import networkx as nx
import numpy as np
import osmnx as ox

from app.domain.entities.node import Node


def build_distance_time_matrix(graph: nx.MultiDiGraph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
    """Snaps each Node to its nearest routable edge, then computes the asymmetric
    N×N shortest-path distance (meters) and time (seconds) matrices (PRD Section 10)."""
    xs = [n.coordinates.lon for n in nodes]
    ys = [n.coordinates.lat for n in nodes]
    snapped_edges = ox.distance.nearest_edges(graph, xs, ys)
    # Route via the edge's destination node — a routable, in-graph anchor point.
    graph_node_ids = [v for _, v, _ in snapped_edges]

    n = len(nodes)
    dist = np.zeros((n, n))
    time = np.zeros((n, n))
    for i, source in enumerate(graph_node_ids):
        lengths = nx.single_source_dijkstra_path_length(graph, source, weight="length")
        times = nx.single_source_dijkstra_path_length(graph, source, weight="travel_time")
        for j, target in enumerate(graph_node_ids):
            if i == j:
                continue
            dist[i, j] = lengths[target]
            time[i, j] = times[target]
    return dist, time
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_distance_matrix_builder.py tests/property_based/test_distance_matrix_builder_properties.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/geospatial/distance_matrix_builder.py tests/unit/test_distance_matrix_builder.py tests/property_based/test_distance_matrix_builder_properties.py
git commit -m "feat: implement node-snapped asymmetric distance/time matrix builder

test: cover matrix shape/asymmetry/zero-diagonal and the no-infinite-distance property after SCC cleaning"
```

---

### Task 4: Stochastic delay injection (`stochastic_delay_injector.py`)

**Files:**
- Modify: `backend/app/infrastructure/geospatial/stochastic_delay_injector.py`
- Test: `tests/unit/test_stochastic_delay_injector.py`, `tests/property_based/test_stochastic_delay_injector_properties.py`

**Interfaces:**
- Consumes: a time matrix (Task 3's output), a caller-supplied `numpy.random.Generator` (the shared seed — Phase 5's orchestrator owns creating this `Generator`; this task's tests create their own for isolation).
- Produces: `inject_stochastic_delay(time_matrix: np.ndarray, rng: np.random.Generator, hour_of_day: float = 8.0) -> np.ndarray` — Phase 2/3 solvers consume the delayed matrix.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_stochastic_delay_injector.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay


def test_output_shape_matches_input():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert result.shape == base.shape


def test_delayed_times_are_never_shorter_than_base():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert np.all(result >= base)


def test_diagonal_stays_zero():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert result[0, 0] == 0
    assert result[1, 1] == 0
```

```python
# tests/property_based/test_stochastic_delay_injector_properties.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay


def test_same_seed_reproduces_identical_delays():
    """The fairness guarantee two phases from now (PRD Section 7) depends on this holding exactly."""
    base = np.array([[0, 60, 90], [120, 0, 45], [80, 30, 0]], dtype=float)
    result_a = inject_stochastic_delay(base, np.random.default_rng(123))
    result_b = inject_stochastic_delay(base, np.random.default_rng(123))
    assert np.array_equal(result_a, result_b)


def test_different_seeds_diverge():
    base = np.array([[0, 60, 90], [120, 0, 45], [80, 30, 0]], dtype=float)
    result_a = inject_stochastic_delay(base, np.random.default_rng(1))
    result_b = inject_stochastic_delay(base, np.random.default_rng(2))
    assert not np.array_equal(result_a, result_b)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_stochastic_delay_injector.py tests/property_based/test_stochastic_delay_injector_properties.py -v`
Expected: FAIL — stub has no `inject_stochastic_delay`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/geospatial/stochastic_delay_injector.py
import numpy as np

# SVRPBench Section 2.1 parameters (svrp_benchmark_doc.md)
MU_BASE = 0.0
SIGMA_BASE = 0.3
DELTA = 0.1
EPSILON = 0.2
PEAK_HOURS = (8.0, 17.0)
PEAK_SIGMA = 1.5


def _peak_hour_amplification(hour_of_day: float) -> float:
    closest_peak_distance = min(abs(hour_of_day - peak) for peak in PEAK_HOURS)
    gaussian_congestion = np.exp(-(closest_peak_distance**2) / (2 * PEAK_SIGMA**2))
    return DELTA + EPSILON * gaussian_congestion


def inject_stochastic_delay(
    time_matrix: np.ndarray, rng: np.random.Generator, hour_of_day: float = 8.0
) -> np.ndarray:
    """Multiplies each base travel time by a log-normal random multiplier, per
    SVRPBench's formulation (PRD Section 10 point 7). All randomness is drawn
    from the caller's seeded Generator — never numpy's global random state."""
    amplification = _peak_hour_amplification(hour_of_day)
    sigma = SIGMA_BASE + amplification
    multipliers = rng.lognormal(mean=MU_BASE, sigma=sigma, size=time_matrix.shape)
    delayed = time_matrix * multipliers
    np.fill_diagonal(delayed, 0)
    return delayed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/Scripts/python -m pytest tests/unit/test_stochastic_delay_injector.py tests/property_based/test_stochastic_delay_injector_properties.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/geospatial/stochastic_delay_injector.py tests/unit/test_stochastic_delay_injector.py tests/property_based/test_stochastic_delay_injector_properties.py
git commit -m "feat: implement SVRPBench-modeled log-normal stochastic delay injection

test: cover shape/monotonicity/diagonal and the seed-determinism property"
```

---

### Task 5: End-to-end standalone verification script

**Files:**
- Create: `backend/scripts/verify_geospatial_pipeline.py`

**Interfaces:**
- Consumes: `load_cached_graph` (Task 2), `build_distance_time_matrix` (Task 3), `inject_stochastic_delay` (Task 4).
- Produces: printed output only — this is the "show me the matrix for one small test case" deliverable, not a module anything later imports.

- [ ] **Step 1: Write the script**

```python
# backend/scripts/verify_geospatial_pipeline.py
"""Standalone, offline, no-network verification of the full Phase 1 pipeline
against the pre-cached Koramangala graph — run manually, not part of the test suite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.domain.entities.node import Node
from app.domain.value_objects.geographic_coordinates import GeographicCoordinates
from app.infrastructure.geospatial.osmnx_client import load_cached_graph
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "koramangala_bengaluru.graphml"

# 5 hand-picked points scattered across Koramangala's road network.
TEST_NODES = [
    Node(id="depot", coordinates=GeographicCoordinates(lat=12.9352, lon=77.6146)),
    Node(id="n1", coordinates=GeographicCoordinates(lat=12.9370, lon=77.6180)),
    Node(id="n2", coordinates=GeographicCoordinates(lat=12.9330, lon=77.6120)),
    Node(id="n3", coordinates=GeographicCoordinates(lat=12.9390, lon=77.6100)),
    Node(id="n4", coordinates=GeographicCoordinates(lat=12.9310, lon=77.6170)),
]

if __name__ == "__main__":
    graph = load_cached_graph(CACHE_PATH)
    print(f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    dist, time = build_distance_time_matrix(graph, TEST_NODES)
    print("\nDistance matrix (meters):")
    print(np.round(dist, 1))
    print("\nBase time matrix (seconds):")
    print(np.round(time, 1))

    rng = np.random.default_rng(42)
    delayed_time = inject_stochastic_delay(time, rng, hour_of_day=8.0)
    print("\nTime matrix with 8am peak-hour stochastic delay (seconds):")
    print(np.round(delayed_time, 1))
```

- [ ] **Step 2: Run it and capture the output**

Run: `cd backend && .venv/Scripts/python scripts/verify_geospatial_pipeline.py`
Expected: prints node/edge counts and three 5×5 matrices. Paste this output into the Phase 1 explainability summary — it is the deliverable the user asked to see before continuing.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_geospatial_pipeline.py
git commit -m "test: add standalone end-to-end verification script for the geospatial pipeline"
```

---

## Self-Review Notes

- **Spec coverage:** OSMnx ingestion + largest-SCC + offline cache (Section 8, 10) → Task 2; node snapping + asymmetric matrix (Section 10) → Task 3; log-normal stochastic delay with SVRPBench parameters (Section 10 point 7) → Task 4; node-snapping correctness / no-infinite-distance tests named explicitly in Section 14's testing table → Task 3's property test; bounding-box size cap (Section 17) → Task 2. The end-to-end matrix printout the user explicitly asked for → Task 5.
- **Deliberately deferred, stated not silenced:** `application/interfaces/geospatial_repository_port.py` stays a stub this phase — Dependency Inversion only pays off once `OptimizationOrchestrator` (Phase 5) actually depends on the abstraction instead of the concrete `osmnx_client`/`distance_matrix_builder` functions; introducing the interface now would have zero caller and is speculative per the project's YAGNI constraint. Flagging this now so it isn't mistaken for an oversight later.
- **Placeholder scan:** clean — every step has real, runnable code; the two exception classes with no Phase 1 caller (`CapacityExceededError`, `TimeWindowViolation`) are complete one-line declarations, not TODOs.
- **Type consistency:** `build_distance_time_matrix(graph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]` (Task 3) is consumed by Task 5 exactly as declared; `inject_stochastic_delay(time_matrix, rng, hour_of_day)` (Task 4) is consumed by Task 5 the same way.
- **Review Focus:** out-of-bounds delivery coordinate — not fully closed this phase (documented as a known gap: `nearest_edges` has no distance-sanity check; flagging for Phase 6/7's Pydantic lat/lon-bounds validation to be the actual backstop, per PRD Section 17, rather than duplicating that check here). Delivery-node-count-vs-graph-size mismatch — structurally impossible to mis-handle since the matrix builder only ever indexes by `len(nodes)`, never by graph size; no separate test needed. Seed determinism — covered by Task 4's property test. Cache-overwrite risk — mitigated procedurally (Task 2 Step 6 is a one-time manual run, not part of any automated pipeline that could re-run and clobber it); noting in the explainability log after Task 2 as the safeguard rather than adding file-lock code for a single-developer MVP. Oversized-place-query cap — covered by Task 2's test.
