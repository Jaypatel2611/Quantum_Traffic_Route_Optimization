# SIH26137 — Egreen Quanta: Build Explainability Log

Source of truth: `SIH26137_Implementation_PRD.md`, `SIH26137_Design_Brief.md`.
Updated after every phase and every noticeable change.

## Phase 0 — Scaffolding

**What was built:**
- DDD-structured FastAPI backend (`backend/app/{domain,application,infrastructure,presentation}`) with stub modules for every Phase 1–7 file named in PRD Section 18, each docstring-tagged with the phase that fills it in.
- `backend/app/main.py`: FastAPI app with CORS middleware and an async `/health` endpoint, covered by an integration test.
- A Vite+React+TypeScript frontend (`frontend/`) whose `App.tsx` fetches `/health` on mount and renders the live status, covered by a mocked-fetch component test.
- `docker-compose.yml` wiring both services; both build and run via `docker compose up --build`.
- Dependencies pinned to exact resolved versions in both `backend/requirements.txt` (via `pip freeze`) and `frontend/package.json`/`package-lock.json` (stripped of `^`/`~` ranges).
- A dedicated git repository for this project (previously nested inside an unrelated personal monorepo) and a GitHub remote (`Jaypatel2611/Quantum_Traffic_Route_Optimization`) pushed after every task.

**What was deliberately deferred:** all algorithm/geospatial logic (empty stub modules only), per this phase's explicit scope.

**Bugs caught and fixed during this phase's own verification (not silently patched over):**
1. `docker-compose.yml`'s `environment: VITE_API_BASE_URL=...` on the frontend service was a no-op — Vite bakes `import.meta.env.*` values in at `npm run build` time, not container runtime, so a compose-level env var can never reach an already-built static bundle. Fixed by adding `frontend/.env.production` (read at build time inside the Dockerfile's `RUN npm run build` step) and removing the dead compose key.
2. A `curl` against `/health` returned `200 {"status":"ok"}`, but the actual browser page at `http://localhost:4173` showed "Backend status: unreachable" — curl doesn't enforce CORS, browsers do. The backend's `allow_origins` only listed the Vite dev-server origin (`:5173`), not the Compose-served demo origin (`:4173`), so the browser silently discarded the (successful, 200-logged) response before JS could read it. Caught by actually loading the page in a browser and reading network/console state, not by curl alone. Fixed by adding `:4173` to `allow_origins`, with a regression test (`test_health_allows_cors_from_docker_compose_frontend_origin`) confirmed RED before the fix and GREEN after.

**How to verify:** `docker compose up --build`, then `curl http://localhost:8000/health` and load `http://localhost:4173` in a browser — expect "Backend status: ok".

**Open questions/flags:** none.

## Phase 1 — Geospatial Pipeline

**Task 1 — domain types:** `GeographicCoordinates` (immutable, lat/lon-bounds-validated), `Node` (id/coordinates/demand, demand ≥ 0), and the three domain exceptions (`GraphDisconnectedError`, `CapacityExceededError`, `TimeWindowViolation`) implemented, 8 unit tests.

**Task 2 — offline OSMnx fetch-and-cache pipeline (`osmnx_client.py`):** `fetch_and_cache_graph` (bounding-box size guard → fetch → largest-strongly-connected-component truncation → edge speed/travel-time imputation → `.graphml` save) and `load_cached_graph` (zero-network load). 2 mocked unit tests.

**Flagged deviations, not silently substituted:**
1. PRD Section 8's example place string, `"Koramangala, Bengaluru, India"`, does not currently resolve to a polygon in Nominatim (verified directly — `ox.geocode_to_gdf` raises `TypeError: Nominatim did not geocode query ... to a geometry of type (Multi)Polygon` for three phrasings of the name). This is external OSM/Nominatim data, not a bug in this pipeline. Flagged to the user, who approved swapping to `"Indiranagar, Bengaluru, India"` (confirmed to resolve to a real polygon) as the Phase 1 test city — same mechanism, same city (Bengaluru), only the neighborhood name changed.
2. PRD Section 8's code snippet calls `ox.add_edge_speeds(G)` with no arguments. Against the installed `osmnx==2.1.1`, this raises `ValueError: This graph's edges have no preexisting 'maxspeed' attribute values so you must pass hwy_speeds or fallback arguments` — osmnx's API tightened since the PRD was written; it no longer silently applies a builtin default-speed table when a graph has zero `maxspeed` tags. Fixed by passing `hwy_speeds`/`fallback` explicitly, using the same residential≈30 km/h / primary-arterial≈60 km/h values PRD Section 10 point 4 itself describes (`HWY_SPEEDS_KMH`/`FALLBACK_SPEED_KMH` in `osmnx_client.py`) — implements the PRD's stated intent through the current library's actual required call shape.

**Real cache generated:** `cache/indiranagar_bengaluru.graphml` — 316 nodes, 829 edges, fetched once from live Overpass/Nominatim and committed to the repo (PRD Section 8: the running app only ever loads this file, never fetches live at demo time). Note: Phase 0's `.gitignore` originally excluded `cache/*.graphml` (added speculatively, before this phase clarified the cache file itself is a required, committed demo asset, not a build artifact) — corrected before committing.

**Task 3 — node-snapped asymmetric distance/time matrix builder (`distance_matrix_builder.py`):** `build_distance_time_matrix(graph, nodes)` snaps each node to its nearest routable edge (`ox.distance.nearest_edges`, not nearest raw node) and computes all-pairs shortest-path distance (meters) and time (seconds) via `networkx.single_source_dijkstra_path_length`. 4 tests (unit + the "no infinite distance after largest-SCC cleaning" property PRD Section 14 names explicitly).

**Bug caught and fixed:** the first implementation anchored every snapped point on its edge's *destination* node unconditionally. Two points that both bordered the same edge (one nearer its start, one nearer its end) silently collapsed onto the same graph node, zeroing the distance between them — caught by the asymmetry test failing (`time[0,1] == time[1,0] == 0.0` when it should not have been equal at all). Fixed by anchoring on whichever of the edge's two endpoints is actually nearer to the query point. Re-verified against the real Indiranagar graph after the fix (asymmetric, finite, sensible 10–90s magnitudes at neighborhood scale).

**Task 4 — SVRPBench log-normal stochastic delay injection (`stochastic_delay_injector.py`):** `inject_stochastic_delay(time_matrix, rng, hour_of_day)`, using SVRPBench's `mu_base=0, sigma_base=0.3, delta=0.1, epsilon=0.2` with Gaussian peak-hour amplification at 8am/5pm (`sigma=1.5`). All randomness drawn from the caller's seeded `numpy.random.Generator` — never global `numpy.random` state, so the same seed reproduces identical delays (verified as a property test; this is the exact guarantee the QPSO/OR-Tools fairness comparison two phases from now depends on).

**Flagged interpretation:** a raw `lognormal(mean=0, sigma)` draw has median 1.0 but ~50% of draws fall below it, which would mean arriving *faster* than the deterministic free-flow base time — contrary to what "stochastic delay" means. Multipliers are floored at 1.0 (`np.maximum(multipliers, 1.0)`) so delay only ever adds time. Not stated explicitly in PRD Section 10 point 7's prose; this is the defensible reading applied and flagged here rather than guessed silently.

**Task 5 — end-to-end verification (`backend/scripts/verify_geospatial_pipeline.py`):** ties the pipeline together against the real cached Indiranagar graph with 5 hand-picked delivery points. Output (8am peak-hour delayed time matrix, seconds):
```
[[  0.   64.8  18.5 113.1  30. ]
 [ 50.9   0.   62.7  40.2  68.1]
 [ 62.8 137.6   0.  168.8  24.1]
 [ 24.2  50.1  36.    0.   54.2]
 [ 50.   68.1 128.6  94.6   0. ]]
```
Every delayed value ≥ its base-time counterpart; matrix stays asymmetric.

**How to verify:** `cd backend && .venv/Scripts/python scripts/verify_geospatial_pipeline.py` (no network access required — loads the committed `.graphml` cache only), or `pytest tests/` for the full 21-test suite.

**Open questions/flags:** none outstanding — both flagged deviations above were resolved with the user's explicit sign-off or a stated defensible interpretation.

## Phase 2 — Classical Baseline (OR-Tools)

**What was built:**
- `Vehicle` (id/capacity/`fuel_type` — scaffolded now per PRD Section 6, unused until Phase 4/V2 heterogeneous fleets) and `Route` (vehicle_id/node_sequence/total_distance_m/total_time_s) domain entities.
- `or_tools_baseline.py`: `solve_cvrp(...)` — single-depot, homogeneous-fleet CVRP via `ortools.constraint_solver.pywrapcp`, configured exactly per PRD Section 9.2 (`PATH_CHEAPEST_ARC` first-solution strategy, `GUIDED_LOCAL_SEARCH` metaheuristic, hard wall-clock `time_limit`). Optimizes on **time** (the post-stochastic-delay matrix), reports distance post-hoc — stated explicitly since PRD doesn't pin the objective metric down for OR-Tools specifically.
- End-to-end verification against the real cached Indiranagar graph, same 5-node case as Phase 1 with demands assigned.

**Flagged, verified directly (not assumed from the PRD's prose):** PRD Section 7 says OR-Tools seed-parity "must be verified against the installed OR-Tools version before the fairness claim is presented to judges" — inspected `ortools==9.15.6755`'s `RoutingSearchParameters` full proto field list directly; confirmed no `random_seed` field exists. This is reported as a visible `seed_configurable: False` field in `solve_cvrp`'s return metadata (covered by its own test), not a comment nobody reads — the QPSO/OR-Tools fairness comparison two phases from now is time-budget-matched, not RNG-state-matched, on the OR-Tools side, and that limitation is now logged wherever the metadata is logged.

**Bug caught and fixed (test-design bug, not implementation):** the first capacity-constraint test used `capacity=50` with demands `[30, 40, 25]` — genuinely infeasible by construction (every pairwise combination of two demands exceeds 50, but only 2 vehicles were offered for 3 customers). `solve_cvrp` correctly raised its "no feasible solution" error; the test itself was wrong. Fixed by choosing `capacity=70` (every pairwise combination fits, but no single vehicle can carry all three — still a real, meaningful capacity constraint, just not an impossible one).

**Real result on the Indiranagar 5-node case** (depot demand 0, n1–n4 demands 30/40/25/35, capacity 100, 2 vehicles, 5s time limit, same 8am-peak-delayed time matrix as Phase 1):
```
Solver config: {'seed_configurable': False, 'time_limit_s': 5.0, 'first_solution_strategy': 'PATH_CHEAPEST_ARC', 'local_search_metaheuristic': 'GUIDED_LOCAL_SEARCH'}

2 route(s) found:
  v0: depot -> n1 -> n3 -> depot
    distance: 1325.5 m, time: 129.2 s
  v1: depot -> n2 -> n4 -> depot
    distance: 818.2 m, time: 92.6 s

Total across all routes: 2143.6 m, 221.8 s
```
Capacity constraint correctly forced a 2-vehicle split (130 total demand > 100 single-vehicle capacity); every route respects its 100-unit cap (v0: 55, v1: 75).

**How to verify:** `cd backend && .venv/Scripts/python scripts/verify_or_tools_baseline.py`, or `pytest tests/` for the full 29-test suite.

**Open questions/flags:** none outstanding.

## Phase 3 — QPSO Algorithmic Engine (highest-risk phase — user flagged, extra care taken)

**What was built:** `qpso_solver.py`, PRD Section 9's QPSO built up from six independently-tested pieces: Rank-Order Value mapping (Task 1), giant-tour-to-per-vehicle-route splitting + PRD Section 12's dynamic capacity penalty (Task 2), multi-objective fitness with Min-Max normalization (Task 3, `FitnessScore` value object), the core iteration loop — local attractor, mean-best position, Monte Carlo position update with a 50/50 sign draw, adaptive α schedule, seeded RNG, wall-clock time budget (Task 4), the Section 15 stagnation countermeasure (Task 5), and a head-to-head verification script against Phase 2's OR-Tools baseline under identical seed/time-budget (Task 6).

**Flagged, user-approved design decision (a genuine spec gap, not guessed silently):** PRD Section 9 fixes the particle to `X_i ∈ R^N` (customer count only) but never states how one permutation becomes multiple vehicle routes. Confirmed with the user: fixed, equal-ish contiguous chunks in tour order, so an over-capacity chunk stays reachable and penalizable (Section 12) rather than auto-repaired away.

**Bug caught and fixed (via the Task 6 verification script, not a test — exactly what that step is for):** the first implementation recomputed the Min-Max normalization range fresh every iteration. Under Min-Max normalization, whichever particle is currently smallest *always* normalizes to exactly 0 (it *is* that population's minimum, by definition) — so Gbest's reported fitness was permanently `0.0` across all 500 iterations, a completely flat, uninformative convergence signal. Task 4's own "Gbest never increases" test didn't catch it, because a constant `0.0` trivially satisfies "never increases." Fixed by tracking a running, expanding (never-shrinking) min/max across the whole run instead of resetting it every iteration, per PRD Section 11's "tracked per-run" wording.

**Clarified, not a second bug (verified by deliberately reproducing it, not assumed):** even after the fix, the real Indiranagar 5-node case *still* shows `fitness: 0.0000` and QPSO landing on the exact same route split as OR-Tools. This is mathematically correct, not degenerate — Min-Max normalization structurally floors whichever particle is simultaneously best on both objectives to exactly 0, and for a tiny 5-customer/2-vehicle search space (only a handful of distinct reachable route-splits), it's expected that both solvers find the same optimum immediately. Confirmed the fix generalizes correctly by testing a bigger (12-customer), *uncorrelated*-objective synthetic instance (independent random distance and time matrices, not one a fixed multiple of the other): convergence history there showed genuine, non-degenerate improvement (`0.3507 → 0.1326 → ... → 0.0651` across 200 iterations, 7 distinct values) — added as a permanent regression test (`test_convergence_is_genuine_not_degenerate_on_an_uncorrelated_instance`) so a future normalization regression can't hide behind "well it's just a small instance" again.

**Real result on the Indiranagar 5-node case, same seed/time-budget as OR-Tools (5s):**
```
=== OR-Tools baseline ===
  v0: depot -> n1 -> n3 -> depot  (dist 1325.5 m, time 129.2 s)
  v1: depot -> n2 -> n4 -> depot  (dist 818.2 m, time 92.6 s)
  total: 2143.6 m, 221.8 s

=== QPSO ===
  v0: depot -> n2 -> n4 -> depot
  v1: depot -> n1 -> n3 -> depot
  total: 2143.6 m, 221.8 s, fitness: 0.0000

OR-Tools: 221.8 s | QPSO: 221.8 s | delta: +0.0% | winner: QPSO (tie)
```
Both solvers agree exactly (route split identical, vehicle labels swapped) — explainable per the paragraph above, not suspicious. **Meaningful QPSO-vs-OR-Tools differentiation is expected at the 50–100 node scale** (PRD's own empirical success metrics: ≥65% win rate, <1% optimality gap), which is Phase 7's validation step, not this one — this phase's job was to prove the algorithm is mathematically correct and produces genuine, reproducible convergence, which the regression test above now locks in independent of instance size.

**How to verify:** `pytest tests/` (43 tests total, including a Hypothesis property test and the new convergence-genuineness regression test), or `cd backend && .venv/Scripts/python scripts/verify_qpso_vs_ortools.py` for the head-to-head comparison.

**Open questions/flags:** none outstanding.
