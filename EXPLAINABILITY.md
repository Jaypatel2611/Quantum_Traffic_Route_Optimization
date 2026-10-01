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

## Phase 4 — Ecological Metrics (COPERT)

**What was built:** `copert_model.py` — `emission_factor_g_per_km(speed_kmh)` (CO2 g/km, clamped to a validated speed domain), `route_emissions`/`total_emissions_kg` (per-route and per-solution CO2 in kg, from average speed), `co2_reduction_percent` (the primary reported sustainability metric). `CO2EmissionProfile` domain value object.

**Real, cited source — verified via web search, not recalled from memory:** three independent search queries converged on the same EMEP/EEA Guidebook-derived COPERT formula for diesel passenger cars <2.5t, valid 10–130 km/h: `CO2(v) = 286 − 4.07v + 0.0271v²` g/km. This is a direct quadratic in `v`, not PRD Section 13's illustrative `(a+bv+cv²)/v` rational form — using the real, verifiable published curve was judged more defensible than force-fitting an approximation to match an illustrative snippet.

**Methodology decision, made explicitly with the user (a genuine PRD tension, not silently resolved either way):** PRD Section 13 asks for COPERT's *shape* rescaled by an *IPCC per-liter-fuel* magnitude, specifically because COPERT's published numbers are European-fleet-calibrated. Doing that rescale would need an assumed India-specific fuel-economy figure (L/100km) with no confidently sourced number — a second, less-verifiable guess stacked on the first. **Decision: use COPERT's real formula (shape *and* magnitude) as-is**, with the European-fleet-calibration caveat stated directly in code (`EMISSION_FACTOR_SOURCE`, tested), not just in this doc. ARAI/CPCB India-specific coefficients are flagged as a V2 dependency. Per the user's explicit instruction, this caveat also needs to reach the eventual assumptions modal (Phase 6/7) and any pitch-deck slide — noting that dependency here so it isn't lost.

**Primary reported metric, per user correction:** the **relative % CO2 reduction** between OR-Tools and QPSO routes, not the absolute kg figure — absolute kg is shown only as secondary, clearly-labeled European-proxy context.

**Flagged simplification (stated, not silent):** emissions computed from each route's **average speed** (`distance/time`), not true per-edge `EF(v)` integration — Phase 1's matrices are aggregated point-to-point sums, not retained edge paths. `# ponytail` comment in code names the upgrade path (track edge paths in `distance_matrix_builder` if per-edge fidelity is needed later).

**Bug caught (mine, not the formula's):** my own hand-computed reference values for the Section 14-required 3-speed-band unit test had small arithmetic slips (e.g. `0.0271×16900` ≈ 457.99, I'd written 458.19) — the sourced coefficients and code were correct throughout; only my manual verification arithmetic needed fixing, caught by the test itself failing against the actual (correct) computed output.

**Real result on the Indiranagar 5-node case** (same seed/time-budget as Phase 3):
```
Emission factor source: EMEP/EEA Guidebook COPERT formula, diesel passenger car <2.5t,
European-fleet-calibrated (ARAI/CPCB India-specific coefficients: V2 dependency)

OR-Tools baseline CO2: 0.3794 kg
QPSO CO2:              0.3794 kg

Relative CO2 reduction (QPSO vs. OR-Tools): +0.00%
```
Same explanation as Phase 3's tie: both solvers found the identical route split for this tiny 5-node/2-vehicle instance, so identical emissions are expected, not a bug. Re-ran fresh before committing — output was bit-identical both times. Meaningful CO2 differentiation is expected at the 50–100 node scale (Phase 7), same caveat as Phase 3's time-based comparison.

**How to verify:** `pytest tests/` (53 tests total), or `cd backend && .venv/Scripts/python scripts/verify_emissions_delta.py`.

**Open questions/flags:** the European-fleet-calibration caveat needs to reach Phase 6/7's assumptions modal UI and the eventual SIH pitch deck (per the user's explicit instruction) — flagged here so it isn't dropped when those phases are built.

## Phase 5 — Async Execution + SSE Streaming

**What was built:**
- `SolverPort` protocol + `run_ortools_job`/`run_qpso_job` adapters (uniform `{"routes": list[Route], "meta": dict}` shape over both solvers). `run_qpso` gained one additive, backward-compatible `progress_list` parameter.
- `OptimizationOrchestrator` (`application/services`) — owns the shared seed/time-budget, runs both solvers concurrently via `asyncio.get_running_loop().run_in_executor(ProcessPoolExecutor, ...)`, with genuine cross-process live convergence streaming through a `multiprocessing.Manager().list()` proxy. Exceptions from either solver are caught at the `asyncio.gather` boundary and reported as an explicit error status.
- `convergence_event_stream` (`presentation/sse`) — SSE generator with full-history replay from index 0 on reconnect, terminating on both `done` and `error` (never an infinite spinner).
- Minimal, explicitly temporary HTTP wiring directly in `main.py`: `POST /jobs` + `GET /jobs/{id}/stream` — no Pydantic validation yet (Phase 7's job); not `optimize_router.py`/`scenario_router.py` (still Phase 6/7 stubs).

**Real bug caught live (via Task 5's verification script, not a test):** `OptimizationOrchestrator.__init__` eagerly spawned a real `Manager()` subprocess, and `main.py` constructs the orchestrator at **module import time**. Every process importing `app.main` — including every `ProcessPoolExecutor` child re-importing the entry script under Windows' `spawn` start method — retriggered that subprocess spawn, tripping Python's recursive-bootstrap guard (`RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase`). This didn't surface in any unit/integration test because pytest's own invocation already sits behind a proper `__main__` guard; it only appeared when running the app as a real standalone script, exactly the scenario Task 5 exists to check. Fixed by deferring `Manager()` creation to first `run_comparison` call. Re-verified live after the fix: no crash, real SSE events streamed.

**Result verified honestly, not spun as a perfect match to the plan's expectation:** the plan expected progress events "spread across the ~8s run"; the actual run showed nearly all progress events landing within the first ~1 second, then a 7-second gap, then `complete`. Diagnosis: QPSO (30 particles, 4 customers) finishes its full 500-iteration budget in under a second for this tiny instance, while OR-Tools deliberately consumes its entire 8s `time_limit` (`GUIDED_LOCAL_SEARCH` keeps searching for the full budget even after finding the optimum — standard OR-Tools time-limit behavior). `asyncio.gather` only resolves once both finish. The 7-second gap between the last progress event and `complete` is itself the proof this is genuinely live, not buffered-to-the-end — a faked/non-live implementation would show everything, including `complete`, in one clump.

**PRD Section 14's named integration test** (`/health` stays sub-100ms responsive during a concurrent solver run) passes for real — verified via `TestClient`'s shared event loop, not a trivial pass.

**Flagged deviations, all stated above, not silent:** (1) orchestrator payload is a full CVRP problem bundle, not PRD Section 7's single-`matrix` illustrative sketch; (2) Task 4's HTTP endpoints are explicitly temporary; (3) "live convergence chart" interpreted as the raw SSE data feed (chart UI is Phase 6's job).

**How to verify:** `pytest tests/` (65 tests total — note: the orchestrator/endpoint tests spawn real OS subprocesses and take longer than earlier phases' suites, ~45-50s), or `cd backend && .venv/Scripts/python scripts/verify_sse_live_stream.py` for the live end-to-end demonstration.

**Open questions/flags:** none outstanding.

## Phase 6 — Frontend Screens

**What was built:**
- Backend bridging endpoints, added to the same explicitly-temporary `main.py` wiring as Phase 5's `/jobs` (real `presentation/schemas`/routers stay a later phase): `GET /cities` (data-driven catalog, one real entry today — Indiranagar, Bengaluru), `POST /jobs/from-nodes` (raw CSV-derived lat/lon nodes + city id → cached-graph matrix build via the existing Phase 1 pipeline → `OptimizationOrchestrator`, same contract as `/jobs`), and `GET /jobs/{id}/result` (serialized routes + CO2/fuel/time-saved deltas for the Results and Green Impact screens — the `complete` SSE event itself carries no route data, so this closes that gap). `or_tools_baseline.py` gained a pinned `ORTOOLS_VERSION` constant surfaced in the fairness footer.
- React+TypeScript SPA (`frontend/src`): all 5 screens from `SIH26137_Design_Brief.md`'s inventory — City/Network Setup (CSV upload + parse, city select, sticky Run CTA, node-preview map), Live Optimization Run (SSE-driven convergence chart, per-algorithm status cards, fairness footer, error banner), Results Comparison (dual-route map, comparison table, always-visible legend), Green Impact Dashboard (CO2/fuel/time stat cards, sourced-assumption modal), How It Works modal (QPSO formulas, reproducibility footer). Deck.GL for route maps (originally straight node-to-node lines because the matrix pipeline kept no road paths; superseded by road-following geometry, see "Post-Phase-8 — Road-Following Route Geometry" below), Recharts for the convergence chart, both named explicitly by the PRD's own stack decision.
- Design-token system in `index.css` matching the brief's Section 3 exactly (color, Inter/IBM Plex Mono type scale, 4px spacing scale, small fixed radii, lightness-stepped elevation, no light mode).

**Scope cuts, stated not silent:** (1) accident-edge injection (Flow C) ships as a present-but-disabled toggle — real edge-level graph selection needs a graph-edge API this phase didn't build; (2) the Green Impact caption "vs. unoptimized nearest-neighbor baseline" from the brief is rendered instead as "vs. OR-Tools baseline," since no separate naive/nearest-neighbor solver exists in this codebase (only OR-Tools + QPSO were ever built) and inventing a third throwaway solver just for a caption was out of scope; (3) fuel-saved liters are derived from the CO2 delta via a stated, sourced constant (2.68 kgCO2/liter diesel, IPCC/EPA default), not an independent measurement.

**Built with the `impeccable` design skill, per explicit user instruction** (also `ui-ux-pro-max` was considered but not needed — the design brief already fully specified tokens/layout, leaving no open aesthetic decision for it to inform): `PRODUCT.md` and `DESIGN.md` record product and visual truth; the build was code-led (no comp round — the visual world was already pinned by the existing brief, not chosen from a concept roll).

**Real defects caught by the finish-review pass** (`impeccable-finish-reviewer` subagent), all fixed and re-verified live in a real browser against the real running backend:
1. `--route-quantum` (QPSO's exclusive amber token per Design Brief P2) had leaked onto six pieces of generic UI chrome — two primary CTAs, two links, the global focus ring, and text selection — diluting the app's one non-negotiable color-encoding rule. Same issue, one instance, for `--accent-eco` on a nav CTA outside the Green Impact dashboard. Fixed: all six now use a neutral `--text-primary` treatment; `DESIGN.md` now states this as a named rule ("The One Meaning Rule") so it isn't reintroduced later.
2. The convergence chart — P1's stated hero element — rendered with no visible line on the small rehearsed-demo scenario: QPSO's fitness collapses to ~0 within the first few of ~500 iterations and stays flush against the x-axis for the rest of the run, reading as an empty chart. Fixed with a padded y-axis domain plus an endpoint marker dot, so a near-flat series still draws as a visible line rather than sitting invisibly on the axis.
3. Two Unicode "ⓘ" glyphs used as icon substitutes (craft-floor's explicit ban) — replaced with a drawn SVG `InfoIcon` (single 1.3px stroke), reused on both trigger buttons.
4. Setup's "Run Optimization" and Results' "View Green Impact →" primary CTAs were reachable only by scrolling on a short viewport, contradicting the brief's own "sticky" wording and the "findable within seconds" judging constraint — both are now genuinely `position: sticky` bottom-pinned.

**Also fixed independently (not a finish-review finding):** a `MapCanvas` container missing `position: relative` let Deck.GL's canvas escape its 70%-width panel and cover the entire page, silently swallowing every click on the page including the Run/View Results buttons — found by testing the real running app in a browser, not by static review.

**How to verify:** `pytest tests/` (69 tests total, backend) and `cd frontend && npx vitest run` (9 tests) both pass; `npx tsc -b` and `npx vite build` are clean. Manual end-to-end verification: `backend/.venv/Scripts/python -m uvicorn app.main:app --port 8000` + `cd frontend && npx vite`, then walk Flow A (CSV upload → Run → live SSE convergence → Results → Green Impact) — confirmed working against the real Indiranagar cached graph, not mocked data.

**Open questions/flags:** the real Phase-7 API surface (`presentation/schemas`, `optimize_router.py`, `scenario_router.py`) is still unbuilt; `/jobs/from-nodes` and `/jobs/{id}/result` are explicitly temporary bridges in the same spirit as Phase 5's `/jobs`, not the final validated contract.

## Phase 6.5 — Bigger Demo Scenario + QPSO Scaling Investigation

**What triggered this:** the only scenario exercised through Phase 6 was the 5-node reference case, where OR-Tools and QPSO happen to find the identical route (the "+0.0%" tie documented back in Phase 4). That's fine for proving the pipeline works, but it can't demonstrate an actual algorithm comparison to a judge. Generated a reproducible bigger scenario instead: `backend/scripts/generate_demo_scenario.py` samples real nodes from the cached Indiranagar graph (guaranteeing every point is on-road and routable) — committed as `docs/demo_scenarios/indiranagar_{15,30,60}.csv`.

**Real bugs found and fixed, in order, each verified by rerunning the bigger scenario:**

1. **Geography-blind route split.** `split_into_routes` divided the QPSO giant tour into fixed-size equal index chunks — a chunk boundary could pair two geographically far-apart customers purely because of where they landed in the permutation. Invisible at 4-5 customers; at 15-60 it made QPSO's real routes dramatically worse than OR-Tools's even though QPSO's own internal fitness had converged. Replaced with a Prins-style DP split that cuts the same fixed tour order at cost-minimizing points, vectorized (the first, unvectorized version of this fix was itself a regression — its O(n²) cost per particle per iteration silently cut QPSO from 500 iterations down to ~100 within the same time budget, trading search depth for a better split; the vectorized version restored full iteration counts). Unit tests in `tests/unit/test_qpso_route_splitting.py`.
2. **NaN-corrupted CO2 payload.** The split fix started legitimately leaving vehicles unused (cheaper than forcing a route). An unused vehicle's route has 0 distance and 0 time, and `route_emissions`' `distance/time` division silently produced NaN (matrix values are numpy floats, which divide 0/0 to NaN rather than raising, unlike plain Python floats) — a NaN float serializes to JSON `null`, nulling out the entire `total_co2_kg`/`green_impact` response. `route_emissions` now returns 0 kg for a 0-distance route. Test in `tests/unit/test_copert_emissions_aggregation.py`.
3. **Dropped tuning parameters.** `/jobs/from-nodes` never forwarded `num_particles`/`max_iterations` from the request into the orchestrator's job payload — every job silently ran with `run_qpso_job`'s bare defaults (30 particles, 500 iterations) regardless of what was requested. Found because two HTTP requests with wildly different particle counts (30 vs 150) produced bit-identical CO2 output; an in-process call to `run_qpso` directly (bypassing the HTTP layer) proved particle count *does* change the result, isolating the bug to the endpoint's payload construction, not the solver. Fixed; regression test asserts the requested value round-trips into `qpso.meta.num_particles`.
4. **Missing local-search refinement (structural, not a bug).** Even after fixes 1-3 — including a diagnostic run at 150 particles, 4000+ max iterations, and a 60-second budget (far beyond the demo's real 15s fairness budget) — QPSO's real CO2/time output barely improved while its internal fitness score improved substantially. This ruled out "just needs more search depth": QPSO's ROV/continuous-position encoding explores route *grouping* globally via the swarm, and the DP split cuts that fixed order well, but neither ever locally polishes the resulting visit *order* the way OR-Tools's own `GUIDED_LOCAL_SEARCH` continuously does for its full time budget. Added `two_opt_route` — a single 2-opt local-search pass over each final route (reorders customers within a route only, never moves a customer between routes, so capacity/demand is untouched) — run once on QPSO's final answer, never inside the per-particle fitness loop. Unit tests in `tests/unit/test_qpso_two_opt.py`.

**Honest result, not spun as fixed:** measured on the 60-node scenario (seed 42, 15s time budget, default 30 particles, vehicle_capacity=150, num_vehicles=9), QPSO's gap to OR-Tools narrowed at each step —

| Stage | QPSO vs OR-Tools CO2 delta |
|---|---|
| Before any of these fixes | -201% (QPSO emits ~3x more CO2) |
| + geography-aware split | -189% |
| + two-opt polish | **-113%** |

Real, measured, roughly-halved improvement — but **QPSO still does not beat OR-Tools at 30-60 node scale**. The remaining gap is in route *assignment* (which customers get grouped onto which vehicle), which neither the split (cuts a fixed order, doesn't reorder customers across the tour) nor two-opt (only reorders within one already-fixed customer set) can touch. Closing that fully would need a different move class entirely (e.g. inter-route customer exchanges/relocations, or a construction heuristic less dependent on the swarm finding a good giant-tour order at high dimensionality) — a real algorithmic redesign, not a bug fix, and out of scope for this pass. **QPSO remains genuinely competitive only at small node counts (≤10-15)** — the 5-node reference scenario's tie is the honest, not degenerate-in-a-bad-way, story; bigger scenarios are demo-honest but currently favor OR-Tools.

**How to verify:** `pytest tests/` (77 tests total, backend); `backend/.venv/Scripts/python scripts/generate_demo_scenario.py <n> <seed>` to regenerate a scenario; `backend/.venv/Scripts/python scripts/verify_bigger_scenario.py` (edit the node count) or POST the CSV's nodes to `/jobs/from-nodes` directly to reproduce the table above.

**Open questions/flags:** whether to keep the 5-node scenario as the rehearsed demo default (honestly competitive) or a bigger one (shows real differentiation but currently unfavorable to QPSO) is a demo-strategy decision, not made here — flagging for the team before the SIH pitch. A proper route-assignment-level local search (or a smarter construction heuristic) is the natural next step if bigger-scenario competitiveness matters for judging.

## Phase 7 — Real Scenario/Optimize API Surface

**What was built:** replaced the temporary, dict-based `/jobs/from-nodes`, `/cities`, and `/jobs/{id}/result` (Phase 6's own explicitly-temporary bridge) with the real routers `presentation/schemas/`, `optimize_router.py`, and `scenario_router.py` had been stubbed for since Phase 0/1's scaffolding:

- **Pydantic schemas** (`presentation/schemas/optimize_request.py`, `optimize_response.py`) replace hand-rolled dict validation. `NodeSchema` enforces lat/lon range and non-negative demand via `Field` constraints; `CreateJobFromNodesRequest` enforces positive capacity/vehicle-count/time-budget and a minimum 2-node list. This is a strictly stronger boundary than Phase 6's version: a wrong *type* (e.g. a string where `vehicle_capacity` expects a float) is now rejected with a clean 422 at the request boundary, where before it would have been silently coerced or crashed deep inside the solver.
- **`GeospatialRepositoryPort`** (`application/interfaces/`) — a Protocol this file's own docstring has said "implemented in Phase 1" since the very first scaffolding commit, actually implemented now: `CachedGraphRepository` (`infrastructure/geospatial/cached_graph_repository.py`) wraps the existing osmnx/distance-matrix pipeline behind `list_cities()`/`build_matrices()`, raising a new `UnknownCityError` (`domain/exceptions.py`) instead of a bare `KeyError` a router would otherwise have to know to catch.
- **`green_impact_calculator.py`** (`application/services/`) extracts the CO2/fuel/time-saved computation out of the router into an independently unit-tested service.
- **Real `APIRouter`s** (`presentation/api/v1/{scenario_router,optimize_router}.py`) wired via FastAPI dependency injection (`presentation/api/v1/dependencies.py`), sharing one `orchestrator` singleton with `main.py`'s still-deliberately-temporary raw-matrix `/jobs` endpoint (Phase 5's own, kept exactly as-is since its existing tests and `scripts/verify_sse_live_stream.py` depend on its raw contract) — a job created by either path streams/resolves through the same `/jobs/{id}/stream` and `/jobs/{id}/result`.

**Verification, not just "it compiles":** every existing black-box HTTP test passed unchanged after the migration — same URL paths, same response shapes — confirming this was a structural refactor, not a behavior change. Re-ran a full job live through the new routers (SSE stream, `/jobs/{id}/result`, `/openapi.json` now lists every endpoint) and walked the entire frontend flow (Setup → Live Run → Results → Green Impact) against the refactored backend in a real browser — all screens rendered correctly, including a real (non-tied) QPSO-vs-OR-Tools delta on the 15-node demo scenario.

**How to verify:** `pytest tests/` (89 tests total, backend); `curl localhost:8000/openapi.json` to see the documented schema; `backend/.venv/Scripts/python -m uvicorn app.main:app --port 8000` + walk the frontend flow manually for the live end-to-end check.

**Open questions/flags:** the raw-matrix `POST /jobs` endpoint in `main.py` is still exactly Phase 5's temporary, unvalidated dict contract — deliberately left alone rather than folded into the new schema, since it serves a different caller (a pre-built-matrix verification script, not the Setup screen's CSV/city flow) and migrating it wasn't asked for. Accident-edge injection (Flow C) still has no backing endpoint; that remains the graph-edge API gap flagged since Phase 6.

## Phase 8 — Accident-Edge Injection (Flow C)

**What was built:** closes the graph-edge API gap flagged since Phase 6/7 — the Design Brief's Flow C (traffic analyst injects a road-accident delay, observes both solvers re-route around it).

- Backend: `GET /cities/{city_id}/edges` (`scenario_router.py`) exposes the cached graph's road segments, deduplicated to one entry per undirected node pair (a `MultiDiGraph` carries a separate directed edge per direction, and sometimes parallel ways between the same two nodes — Flow C selects a segment, not a direction). `POST /jobs/from-nodes` accepts an optional `accident_edge` (a pair of graph node ids from that list); `CachedGraphRepository.build_matrices` multiplies the matching edge's `travel_time` fivefold in a graph copy before computing matrices, so every route that would cross that segment is genuinely slower — verified with a real (not mocked) test: injecting an accident on an actual cached-graph edge multiplies its real time-matrix entry ~5x. `GET /jobs/{id}/result` echoes back which edge was used, for the Results screen's caption.
- Frontend: the Setup screen's "Inject Accident" toggle is real now (was a permanently-disabled placeholder). Toggling fetches the edge list and switches the map into pick mode; clicking a segment stores it, highlights it (dashed red + a "×5 delay" chip), and carries it through `createJob`. Results shows "re-route triggered by an injected accident" when set.

**Real, non-cosmetic bug found and fixed along the way:** a 1.5px line has a hit area far too small to reliably click — true for any real user's mouse, not just an artifact of testing. Confirmed live: a map drag that only *incidentally* crossed a thin edge still triggered its auto-highlight, proving the picking geometry itself worked; deliberate clicks aimed at the same visible line kept missing. Fixed with the standard Deck.GL pattern for this exact problem: a second, wide (16px), visually near-invisible `PathLayer` carries the real pickable/`onClick` hit area, paired with the thin layer that actually gets drawn.

**Also decided in this phase:** the 5-node scenario stays the demo default (Phase 6.5's finding — both solvers tie there, honestly, while bigger scenarios currently favor OR-Tools) rather than a bigger one; `docs/demo_scenarios/indiranagar_5.csv` was added to match the 15/30/60 set, and the Setup screen now pre-seeds it directly (PRD Section 16: no screen is ever actually empty) instead of requiring a manual CSV upload first.

**How to verify:** `pytest tests/` (96 tests total, backend) and `cd frontend && npx vitest run` (10 tests); manual end-to-end check: toggle "Inject Accident," click a road segment, run, and confirm OR-Tools' and QPSO's routes diverge around it on the Results map (they were identical on the 5-node scenario before the accident).

**Open questions/flags:** none outstanding for this phase's own scope. The remaining known limitations (QPSO's route-assignment gap at scale, the raw-matrix `/jobs` endpoint's unvalidated contract) are unchanged from Phases 6.5/7.

## Post-Phase-8 — Hardening Pass (QPSO Polish, Security, Bug Fixes)

**What triggered this:** after the raw-matrix `/jobs` endpoint's Pydantic migration (commit 7c05bd4) and a Windows Smart App Control policy block on pandas got resolved by a reboot (environment issue, not a code bug — confirmed pandas imports clean, all 101 tests passed once `osmnx`/`ortools` were installed), the session moved to closing out known gaps: Phase 6.5's QPSO-vs-OR-Tools route-assignment gap, PRD Section 17's security requirements, and a live UI bug report.

**QPSO relocate-and-swap polish (commit 4f7b426):** added `relocate_and_swap_polish` to `qpso_solver.py` — an inter-route local search (Or-opt relocate + swap, run once after two-opt) that can move a customer between routes, unlike two-opt's within-route-only reordering (Phase 6.5's identified gap: neither the DP split nor two-opt could touch route *assignment*). Unit tests in `tests/unit/test_qpso_relocate_and_swap.py` pass (3/3), and the full suite showed no regressions at commit time. **Not independently re-benchmarked against the 60-node scenario in this pass** — Phase 6.5's -113% CO2 delta table was not re-measured with this change; whether it actually closes the gap is unverified. Flagging honestly rather than claiming a fixed number.

**Security hardening (PRD Section 17, commit bb468cc + this session):**
- Request bodies over 5MB rejected via a `Content-Length` check in `main.py` middleware, before the body reaches Pydantic parsing.
- `extra="forbid"` added to all request schemas (`ForbidExtraModel` base in `optimize_request.py`) — an unexpected field is now a clean 422, not silently ignored.
- List-length caps (`max_length=2000`) on `nodes`/`time_matrix`/`distance_matrix`/`node_ids` as defense-in-depth against a chunked-encoding request that has no `Content-Length` header.
- `time_budget_s` (≤120s), `num_vehicles` (≤50), `num_particles` (≤200), `max_iterations` (≤5000) capped — previously `gt=0` only, so a client could request e.g. `time_budget_s=999999999` and pin both `ProcessPoolExecutor` worker slots indefinitely (found by a security audit pass, not observed in production).
- `depot_index` validated against actual node/matrix length in both `CreateJobRequest` and `CreateJobFromNodesRequest` (was previously unbounded, could `IndexError` deep in the solver).
- Client-side 5MB guard on CSV upload before parsing (`SetupScreen.tsx`), matching the backend cap.
- OpenStreetMap ODbL attribution added to the map canvas (`MapCanvas.tsx`) — required since node/edge geometry derives from OSMnx data even with no live basemap tiles.
- `OptimizationOrchestrator`'s exception handler now logs the full exception server-side (`logger.exception`) and returns a generic `"Solver failed. Check server logs for details."` to the client, instead of echoing `str(exc)` verbatim through `/jobs/{id}/result` and the SSE `event: error` payload — raw internals (paths, shapes, stack detail) no longer leak to an unauthenticated caller.

**Real bug found and fixed — unguarded matrix-dimension crash:** a follow-up `/code-review` pass (high effort, whole-repo) found that `CreateJobRequest` validated each field's *type* but never checked that `time_matrix`/`distance_matrix` were square or matched `node_ids`/`demands` length. A well-formed-per-field but ragged payload (e.g. one short row) passed Pydantic, then hit `np.array(request.time_matrix, dtype=float)` unguarded in `optimize_router.create_job`, raising an unhandled `ValueError` — a raw 500 instead of the clean 422 the endpoint's own docstring promises. Fixed by extending the model validator (`_dimensions_consistent` in `optimize_request.py`) to reject ragged/mismatched matrices before they reach numpy. Verified with `backend/scripts/verify_job_request_dimensions.py` (valid payload still passes; four malformed variants are all now rejected). Left the analogous but harmless duplication between `CreateJobRequest`'s and `CreateJobFromNodesRequest`'s depot-index validators unfixed — extracting a shared helper for two 4-line methods was judged an unrequested abstraction, noted instead of built.

**Real bug found and fixed — canvas native-drag-download:** reported live by testing the running app: left-click-dragging the Deck.GL map canvas (intended as pan) was sometimes hijacked by the browser's native image-drag behavior on `<canvas>`, downloading the raw WebGL canvas content as a PNG (visible as a white-background dot-only image, not the actual dark-themed page) instead of panning the map. Fixed with a single `onDragStart={(e) => e.preventDefault()}` on `MapCanvas.tsx`'s wrapping div (the event bubbles up from the canvas, so no deck.gl-internal change was needed).

**Also removed as genuinely dead code:** `backend/app/domain/entities/vehicle.py` (a `Vehicle` dataclass with zero imports anywhere in the backend — superseded early on by the primitive `demands`/`vehicle_capacity` fields used throughout the solver/API) and its orphaned test `tests/unit/test_vehicle.py`, confirmed via a full-repo dead-code audit (only high-confidence finding out of that pass; everything else audited — large files, `SolverPort` Protocol, `requirements.txt` entries — was judged legitimate/cohesive and left alone).

**Relocate-and-swap polish, now actually benchmarked:** manual UI testing surfaced a negative Green Impact number on a real 15-node upload, prompting a re-run of Phase 6.5's benchmark methodology (`backend/scripts/verify_bigger_scenario.py`, seed 42, real cached-graph nodes) with the relocate-and-swap polish in place:

| Scenario | QPSO vs OR-Tools CO2 delta |
|---|---|
| 5-node (default demo, 2 vehicles) | tie, `+0.0%` |
| 15-node, 5 vehicles | `-7.1%` (QPSO still worse) |
| 60-node, 8 vehicles | `+7.6%` (QPSO now **wins** — was `-113%` before this session's polish) |

Real, honest result: the polish clearly helps at 60-node scale (more routes to relocate customers between), flipping QPSO from 3x-worse to better-than-OR-Tools, but does *not* close the gap at 15 nodes. The mid-scale dip is unexplained and not investigated further this pass — flagging rather than guessing at a cause.

**Real bug found and fixed — infeasible-capacity request crashed instead of being rejected:** while sweeping vehicle counts on the 15-node scenario to investigate the dip above, `num_vehicles=3` (capacity 100 × 3 = 300 < total demand 313) triggered the generic `"Solver failed. Check server logs for details."` message added earlier this session — OR-Tools' `solve_cvrp` already raises a clear, safe `RuntimeError` for this exact case ("check that capacity * num_vehicles covers total demand"), but the orchestrator's blanket `except Exception` (this session's own leak-prevention fix) now hides that good message behind the generic one along with real crashes, making an ordinary user mistake (asking for more capacity than the fleet has) undebuggable from the UI. Fixed at the actual boundary instead of patching the error message: both `CreateJobRequest` and `CreateJobFromNodesRequest` now validate `sum(demand) <= vehicle_capacity * num_vehicles` in their model validators, rejecting an infeasible request with a clean, specific 422 before it ever reaches either solver.

**How to verify:** `pytest tests/` (99 tests, backend) and `cd frontend && npx vitest run` (10 tests) both pass; `npx tsc -b` clean. `backend/scripts/verify_job_request_dimensions.py` exercises the matrix-dimension validator; the feasibility validator was confirmed directly against `CreateJobFromNodesRequest` (161 kg-style overload rejected with a clean `ValidationError`, not a 500).

**Open questions/flags:** the 15-node mid-scale dip (QPSO `-7.1%` there vs `+7.6%` at 60 nodes) is real and unexplained — worth investigating before relying on the relocate-and-swap polish as a blanket "QPSO wins at scale" claim in the pitch; the honest framing is "QPSO ties small, sometimes trails mid-size, wins at 60 nodes" until that's understood. Persona 2's "multi-agent fleet load-balancing" scenario (raised and explicitly deferred this session) remains unbuilt — confirmed not a Section 4 MVP acceptance-criteria item, narrative/pitch framing only; two other SIH26137 submissions checked for reference (`fierce-fly239/quantumroute`, `Shridhar396/SIH26137`) also don't implement it, so no existing pattern to build against if it's picked up later. No auth/session system exists anywhere (by design, for a single-laptop offline demo) — flagged in the security audit as a conscious choice, not a gap, unless this ever moves past demo stage.

---

## Post-Phase-8 — Road-Following Route Geometry

**What triggered this:** looking at the Results screen, the OR-Tools and QPSO routes were straight lines between stops, cutting across blocks where no road exists. The km / minutes / CO2 figures were always road-based (Dijkstra over the OSM graph), so the picture contradicted the table. Cause: `MapCanvas.tsx` drew `node_sequence` (stops only) point to point, and `build_distance_time_matrix` kept only each path's length and time, never the path itself. The straight-line rendering was a deliberate Phase 6 simplification ("line-only routes"), not a solver bug.

**What was built:**
- `distance_matrix_builder.py`: the stop-snapping step was extracted into `_snap_to_graph_nodes` (shared, so the matrix and the geometry cannot snap differently). New `build_route_geometries` returns one `[lat, lon]` polyline per route: for each consecutive stop pair, the fastest (`travel_time`-weighted) path, i.e. the road the reported time came from. Each leg starts and ends at the stop's own coordinates so the line meets the map dot. Legs are cached per (from, to) pair within a call.
- `GeospatialRepositoryPort` / `CachedGraphRepository`: new `route_geometries(city_id, nodes, sequences, accident_edge=None)`. The accident-multiplier graph copy is now a shared `_load_with_accident`, used by both `build_matrices` and `route_geometries`, so the drawn path and the solver's matrices see the same blocked road.
- `optimize_router.py`: `/jobs/from-nodes` remembers `(city_id, nodes)` per job; `GET /jobs/{id}/result` attaches `geometry` to every route of both solvers. Raw-matrix `/jobs` has no city, so those routes get no geometry.
- `RouteResponse.geometry` (optional) and the TypeScript `Route.geometry?`.
- `MapCanvas.tsx`: draws `geometry` when present, falls back to straight stop-to-stop lines when absent. `ResultsScreen.tsx` highlights the blocked segment (red dashed) when the job had an accident.

**Honest limits:**
- Accident detours are now drawn: legs use the accident-modified graph's fastest path, so a blocked road (x5 time) is routed around where an alternative exists. The injected random stochastic delay (log-normal, per matrix cell) still cannot be drawn.
- Distance and time come from two different shortest paths (by length vs by time). The reported km is the shortest-by-length path's length; the drawn line is the fastest path, so its true length can be slightly above the km figure. Unifying them (distance = length of the fastest path) would change the benchmarked numbers and was not done.
- Polylines join graph junctions with straight segments (the grey network is drawn the same way), so very curved roads look slightly angular. OSM edge `geometry` curves are not used.
- Where OR-Tools and QPSO share a road, the dashed orange line sits over the solid blue one.
- Geometry is computed on each `/result` call and the per-job scenario dict is in memory, like the accident-edge dict. Fine for one demo process, not for multi-instance deployment.

**Verification:** new unit tests `test_route_geometry_follows_graph_junctions_not_a_straight_line` (route passes through the only connecting junction, starts/ends at the stops) and `test_route_geometry_detours_around_accident_edge` (blocking the fast road flips the path to the alternative); full suite 101 passed; `tsc -b` clean.

---

## Post-Phase-8 — Node Inspection, Multi-Accident Injection, Back Navigation

**What triggered this:** a UX pass over the Setup -> Live Run -> Results workflow: every CSV node should be inspectable, the Results page should show the optimizer's actual route stop by stop, more than one accident should be injectable at once, and going Back should never lose work.

**Inspected first (nothing about routing was changed):** the solvers (`or_tools_baseline.py`, `qpso_solver.py`) return `node_sequence` per vehicle and optimize over the shared distance/time matrices; demand only enters as a capacity constraint, never as an ordering key. The new UI renders `node_sequence` exactly as returned and never sorts by demand, id or distance (a unit test uses a deliberately unsorted route to guard this).

**Node inspection**
- `MapCanvas` nodes are now pickable. Hover shows node id, demand and lat/lon (and on Results, which vehicle visits it and at which stop for each solver). The tooltip uses `text`, not `html`, because node ids come straight from the user's CSV.
- The depot is now "row 0 of the CSV" on the map (it was `id === 'depot'`), matching what the solver treats as the depot (`depot_index = 0`).
- Setup has a collapsible `NodeTable` of every parsed row. `parseNodesCsv` now rejects duplicate `node_id`s and non-numeric lat/lon/demand cells, since routes, tooltips and tables key on `node_id`.

**Actual route on Results**
- `GET /jobs/{id}/result` adds `stops` per route: for each visit, the leg distance/time and cumulative distance/time, read from the very matrices the solvers optimized over (`_JobContext`, bounded to the last 50 jobs because each holds two N x N matrices). Legs therefore sum exactly to each route's reported totals; an integration test asserts this.
- New `RouteBreakdown` per solver and vehicle: `Depot -> n2 -> n3 -> n1 -> Depot`, then a table with CSV demand, leg/cumulative km and minutes, running load, and route totals against vehicle capacity.

**Multiple accidents**
- Request field `accident_edge` became `accident_edges` (list, max 50); the result echoes `accident_edges`. `CachedGraphRepository._load_with_accidents` multiplies each distinct segment's `travel_time` x5 once (a repeated segment is not x25) on a copy of the cached graph. The matrices, the solvers and the drawn geometry all see the same blocked roads, so rerouting uses the existing optimization path unchanged.
- Setup: clicking road segments in accident mode adds accidents (duplicates ignored); each is listed with its own Remove button, plus Clear all.
- Results: each route leg is drawn along the fastest path with accidents applied. `rerouted_geometry` marks the legs whose path differs from the no-accident path, drawn as a yellow halo under the route lines. A `MapLegend` distinguishes Depot, delivery nodes, accident roads (red dashed) and rerouted paths.

**Navigation / state**
- Setup form state (city, CSV nodes, capacity, vehicles, accidents) moved from component state into `AppState` (`setup` + `updateSetup`), so it survives leaving the screen.
- `goBack`: Live Run -> Setup, Results -> Setup, Green Impact -> Results. Live Run is a transient step (re-entering it would replay the SSE stream into an already-complete history), so Results does not go back to it. Result data is kept, so Green Impact -> Results does not refetch.

**Verification:** backend 104 tests passing (new: multi-accident repository test, stops-sum-to-totals and multi-accident-reroute integration tests against the real solvers); frontend 20 vitest tests passing (CSV validation, nodes+demand display, add/remove/clear accidents, Back preserving state, route order and numbers in `RouteBreakdown`); `tsc -b` clean.

**Limitations**
- Not verified in a real browser this session (the backend was stopped by a low-memory event and was not restarted); hover tooltips and the map overlay are covered by types and component-level tests only, with the map stubbed out in jsdom.
- Going Back from Live Run while a job is running drops that run's result (the stream subscription ends); start it again from Setup.
- ~~The `accident_edge` -> `accident_edges` rename breaks old callers~~ Fixed: `/jobs/from-nodes` still accepts the legacy single `accident_edge` and merges it into `accident_edges` (deduplicated); responses only ever carry `accident_edges`.
- A rerouted leg is flagged only if its road path changes; the solver can also reorder stops because of accidents, which shows up in the route chain, not the halo.
- Accidents are road segments (existing system), not nodes.
- ~~An accident on a segment with no alternative looks like it did nothing~~ Fixed by the Accident impact panel below.

### Accident impact panel
Each accident is now reported per solver as `not_on_route` (no leg's fastest free path uses the road: no effect), `rerouted` (legs used it for free but now drive around it, with the extra time) or `driven_through` (no cheaper way around, so legs still use it, slowed). `build_accident_impacts` judges against the solver's final stop order. `added_time_s` is that accident's own base road-time cost over the legs it crosses (computed with only that accident applied); the random log-normal traffic delay is applied to the whole matrix and is not attributed per road. Status uses the real combined situation: an accident that is avoidable alone becomes `driven_through` if another accident blocks the detour. If the solver reorders stops to avoid an accident entirely, the final order no longer crosses it, so it reads `not_on_route`. Tests: three builder cases (rerouted with exact extra time, driven through, off-route) plus the combined-accidents case, an integration check on the live `/result` payload, and the panel's rendering; backend 111, frontend 32 tests passing.

