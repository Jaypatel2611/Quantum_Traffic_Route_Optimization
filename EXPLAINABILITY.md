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
