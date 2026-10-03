# SIH26137 — Corrected Implementation PRD & Technical Blueprint
## Quantum-Inspired Intelligent Traffic Route Optimization in Transportation Systems Using Metaheuristic Optimization
**Sponsor:** Egreen Quanta · **Problem Statement ID:** 26137 · **Document type:** Engineering-ready PRD (supersedes/extends the Gemini-authored baseline PRD)
**Author context:** Prepared as the corrected, implementation-grade blueprint closing the engineering gaps in the baseline PRD, cross-checked against the official problem statement text and two research documents (SIH26137 deep-dive, SVRPBench paper).

---

## 0. Assumptions Stated Up Front

No clarifying questions were asked because the five dimensions below can be resolved with stated, reasonable defaults. If any assumption is wrong, only the affected subsection needs revision — the architecture does not change shape.

| # | Dimension | Assumption made | Why this default |
|---|---|---|---|
| A1 | Team size | 2–4 person student team, mixed backend/frontend/ML skill | Typical SIH team size; architecture is modular enough for 1 person per layer (algorithms / geospatial / API / frontend) |
| A2 | Demo hardware | Consumer laptop, 8–16 GB RAM, 4–8 CPU cores, no dedicated GPU, Windows or Linux | No component in this blueprint (QPSO, OR-Tools, OSMnx, FastAPI, React) requires a GPU. GPU-bound components (OPQNN, RL baselines) are explicitly deferred to Phase 2/Later and excluded from MVP hardware planning |
| A3 | Timeline | **Flagged, not assumed silently — see below** | See "Timeline conflict" callout |
| A4 | Simplicity vs. rigor | Balanced: simplicity for infrastructure (no Celery, no Kubernetes, no microservices), full mathematical rigor for the algorithmic core (QPSO formulas, seeding, benchmarking) — because judging criteria reward algorithmic depth, not infra sophistication | SIH judging rubric weighs "technical approach" and "novelty" on the algorithm, not on deployment topology |
| A5 | Scope authority | Baseline PRD (Gemini-authored) is authoritative for WHAT to build; this document only corrects HOW and fills engineering gaps | Per explicit instruction — no invented requirements beyond baseline PRD or the official problem statement text |

**Timeline conflict — flag for the team to resolve immediately:** The research document (`SIH26137_quantum_traffic_routing_deep_dive_formatted.md`) states SIH 2026 submissions are due **30 September 2026**, sourced from a third-party org listing page, not from the official problem-statement text pasted into this task. The baseline PRD's five-year roadmap frames "Phase 1: The SIH Prototype" as a **6-month** effort. These two signals conflict if the 30 Sept date is accurate for the *current* evaluation cycle. This document treats the 6-month Phase 1 framing as the **roadmap narrative** (what the PPT should describe as the prototype's engineering scope) and treats the actual **hands-on-keyboard build window** as unknown and team-supplied. Section 21's "Week 1 build order" is written to be valid whether the team has 7 days or 7 weeks — it is a dependency-ordered checklist, not a calendar. **Action for the team: confirm the actual submission deadline from the official SIH portal before finalizing sprint planning.**

---

## Research Provenance — Three Labeled Sections

Per the research requirement, every non-trivial claim below is tagged by source so historical research is never mistaken for an official SIH26137 requirement.

### (1) Facts verified from the baseline PRD / official problem statement
- Official problem statement text confirms: transportation network modeled as a weighted graph; framework centers on QPSO; benchmarked against "conventional metaheuristics and exact methods"; objectives are travel time, distance, congestion minimization, computational complexity reduction, and smart-city scalability. No emission/ecological objective is named in the *official* problem statement text — the ecological/COPERT/"Egreen" angle is a baseline-PRD and sponsor-branding inference, not an official objective (still valid to pursue, but must not be presented as an official requirement).
- Baseline PRD mandates: OSMnx for real Indian road topology, Google OR-Tools as the classical baseline, SSE-based live convergence streaming, fully offline execution on consumer hardware, no physical QPUs, no paid live traffic APIs for the MVP, no live vehicle telematics/autonomous dispatch, DDD/Clean Architecture folder layout, single-depot/homogeneous-fleet MVP scope, COPERT-based ecological quantification, and the two personas (Enterprise Fleet Manager, Municipal Traffic Analyst).
- Baseline PRD's own success metrics (65% win rate, <1% optimality gap on N=15, 95% convergence within T/3, ≥10% CO2 reduction, <15s E2E latency) are treated as authoritative targets, carried forward unchanged.

### (2) Findings from historical/academic research (last ~5 years, QPSO/QIEA/QUBO + SVRP benchmarking)
- QIEA formalism: each Q-bit is a pair `(α, β)` with `α² + β² = 1`; a quantum rotation gate `U(Δθ) = [[cosΔθ, -sinΔθ],[sinΔθ, cosΔθ]]` nudges amplitudes toward the current best solution; measurement draws `r ∈ [0,1)` and collapses to 1 if `r < β²`. A cited empirical review recommends a static rotation angle of `0.05π` as a solid default, with decreasing dynamic schedules outperforming static ones overall. *(Source: deep-dive research doc, citing peer-reviewed rotation-gate literature.)*
- QPSO (the delta-potential-well / mean-best-position formulation) is the specific variant one real, independently-built SIH26137 competitor team ("quantumroute") implemented and reported honest numbers for: on a 9-stop network with proven optimum 180.71, QPSO reached 181.80 (0.60% gap, σ 0.96) vs. classical PSO's 182.87 (1.20% gap, σ 2.36); on a 49-stop network, QPSO won 20/30 head-to-head trials, mean tour 1347.8 vs. classical PSO's 1356.7. *(Source: deep-dive research doc, historical/competitive intelligence — this is a competitor's reported result, not this team's target, and not an official benchmark.)*
- **The competitive field for this exact problem statement is already crowded**: at least seven independent public repos (QITRO, q-green-corridor, QuantumRoute, quantumroute, others) have shipped working QPSO/QIEA prototypes with maps, convergence charts, and classical-baseline comparisons. A direct review of the most advanced reference implementation found it explicitly does **not** implement ecological/green metrics despite the sponsor being "Egreen Quanta" and having a sibling problem statement (SIH26138) explicitly about fuel/green fleet optimization. *(Source: deep-dive research doc.)* This is the single most load-bearing research finding for this document's differentiation strategy (Section 16, Section 20).
- SVRPBench (NeurIPS 2025 Datasets & Benchmarks, MBZUAI): 500+ stochastic VRP instances, 10–1000 customers, models time-dependent congestion (Gaussian morning/evening peaks, μ=8/17, σ=1.5), log-normal multiplicative delay `R(t)`, Poisson-process accident injection (peaking μ_night=21, σ=2, duration ~U(0.5,2.0) hours), and empirically-grounded bimodal (residential) / single-mode (commercial) time-window sampling. Benchmarked classical/metaheuristic solvers (NN+2opt, Tabu, ACO, OR-Tools) remain robust under stochasticity while RL solvers (POMO, Attention Model) degrade >20% under distributional shift and show CVR/feasibility collapse in multi-depot / large-instance settings (e.g., Tabu/ACO feasibility drops to 0.000 at "depots equal city", size≥100 in the paper's own tables). *(Source: `svrp_benchmark_doc.md`, directly.)* This is the authoritative source for the log-normal delay-injection model this blueprint specifies in Section 10.
- No authoritative India-specific vehicular emission-factor dataset (equivalent in rigor to COPERT's EU factors) was located in the cited research for direct substitution. *(Source: deep-dive research doc, explicitly flagged as an unresolved gap — carried into Section 13 below as a named, sourced proxy decision rather than left unsourced.)*
- A 2025 comparative benchmarking paper on real gate-based quantum optimization (VQE, QAOA) versus classical solvers concludes a standardized benchmarking framework "is still lacking" — supporting this blueprint's decision to frame quantum-inspired search as an exploration/diversification mechanism, not a claim of outright superiority. *(Source: deep-dive research doc, citing arXiv 2503.12121.)*

### (3) This document's own technical recommendations and inferences
Everything in Sections 1–21 below that is not explicitly attributed above is this document's own engineering judgment, applied to close gaps the baseline PRD left open (async execution model, seeding protocol, exact folder tree, testing strategy, demo contingency plan, judging-criteria mapping, and the final library/build-order decision). These are opinionated defaults, not additional official requirements.

---

## 1. Problem Statement

**Business problem.** Indian logistics operators run thin-margin fleets against NP-hard Capacitated Vehicle Routing Problem (CVRP) instances layered on top of genuinely chaotic urban traffic. Excess mileage from sub-optimal routing directly inflates fuel spend, SLA violations, and driver fatigue; simultaneously, naive "shortest path for everyone" routing manufactures secondary congestion on arterials and drives avoidable CO2 emissions. Corporate ESG mandates now require fleet operators to *report*, not just reduce, emissions — a reporting capability existing routing tools largely do not expose.

**Mathematical problem.** The CVRP is NP-hard; at the scale of a real city network the search space is non-convex and multimodal, and — critically for this problem statement — **stochastic**: edge weights (travel times) are random variables (log-normal delay, time-dependent congestion, Poisson-arriving accidents), not fixed constants. A solution that is optimal against the *expected* travel-time matrix can be badly infeasible against a *realized* one.

**Why classical deterministic/greedy solvers fail.** Greedy constructive heuristics (nearest-neighbor, cheapest-insertion) converge to a single trajectory through the search space and cannot backtrack out of it — this is premature convergence. Classical local-search metaheuristics (basic PSO, basic GA) improve on this but still get trapped in deep local optima in highly multimodal landscapes because their update rules are deterministic functions of position/velocity with no mechanism to "tunnel" past a locally-worse region to find a globally-better one. Both classes are additionally *fragile under stochastic delay*: a rigid, pre-computed route has no soft mechanism to absorb a delay — it either holds (by luck) or breaks (triggering an expensive manual re-route or depot return).

**Why physical quantum hardware is unsuitable for a live hackathon demo.** This is a NISQ-era hardware unsuitability argument, not a hand-wave:
- **Qubit-count scaling.** Formulating CVRP as a QUBO for a gate-based device (QAOA) requires binary decision variables for every (customer, position-in-route, vehicle) combination plus slack variables to encode capacity and time-window constraints as penalty terms. Qubit requirements scale at least quadratically with customer count for anything beyond toy instances (~10–15 nodes) — current NISQ devices (tens to a few hundred noisy qubits) cannot host a dense, realistically-constrained CVRP encoding at the 50–100 node scale this PRD targets.
- **Decoherence and error rates.** NISQ qubits decohere on the order of microseconds to low milliseconds; a QAOA circuit deep enough to encode CVRP constraints plus enough ansatz layers (`p`) for solution quality exceeds practical coherence budgets, and gate error rates compound multiplicatively with circuit depth.
- **Barren plateaus.** For QAOA on dense, highly constrained cost Hamiltonians (exactly CVRP's shape once capacity/time-window penalties are added), the variational parameter-optimization landscape exhibits vanishing gradients as problem size and circuit depth grow — the classical optimizer loop that drives QAOA cannot find a descent direction, making convergence to a good solution unreliable at exactly the problem sizes this platform must demo.
- **Live-demo risk.** Even where QPU access exists (D-Wave, IBM), queue times and network dependency on a cloud quantum backend introduce a single point of failure completely incompatible with an offline, time-boxed judging demo.

**Why QPSO is the correct bridging choice, explicitly versus QAOA.** QPSO is a **purely classical algorithm** that borrows the *mathematics* of quantum mechanics (probability-density-based position sampling around a delta-potential well, mean-best-position, wavefunction-collapse-style Monte Carlo update) without requiring any quantum circuit, qubit, or quantum simulator. It therefore inherits none of QAOA's qubit-scaling or barren-plateau failure modes — its search-space dimensionality is governed by classical CPU memory and cycles, not qubit count, and its optimization loop is a straightforward classical metaheuristic (no vanishing-gradient variational circuit to train). This is precisely the reasoning the official problem statement itself signals in its own preamble: physical hardware limitations "prevent... direct large-scale use," so quantum-*inspired* metaheuristics are the intended bridge, not a compromise.

---

## 2. Challenge Constraints and Official Requirements

Extracted and organized from the baseline PRD (all items below are baseline-PRD-derived, not newly invented):

**Mandatory capabilities**
- QPSO as the primary quantum-inspired solver, benchmarked head-to-head against Google OR-Tools as the industrial classical baseline, on identical inputs.
- Real Indian road topology via OSMnx (`ox.graph_from_place`) — not synthetic/toy graphs.
- Stochastic traffic modeling via log-normal delay injection (SVRPBench-derived), not live traffic APIs, for the core MVP.
- COPERT-based ecological quantification (CO2 / fuel savings) tied to the sponsor's "Egreen" branding.
- Live algorithmic telemetry via Server-Sent Events (SSE) streaming convergence data to a React frontend.
- Fully offline execution on consumer-grade hardware.
- Domain-Driven Design / Clean Architecture backend structure.
- Single depot, homogeneous fleet for MVP (multi-depot/heterogeneous fleet explicitly deferred to V2).

**Explicit out-of-bounds deliverables (baseline PRD, restated for engineering clarity)**
- **No physical QPUs** — no D-Wave, no IBM Quantum, no cloud quantum backend calls of any kind in the MVP or the "Later/Experimental" bucket's *default* execution path (D-Wave's Ocean SDK is permitted only in its classical `SimulatedAnnealingSampler`/`LeapHybridBQMSampler`-as-classical-fallback form for the optional stretch QIEA variant — see Section 9's explicit tooling boundary).
- **No paid, live traffic APIs** (Google Maps Directions/Routes, TomTom) for the *core MVP demo path*. A TomTom Matrix API fallback is explicitly Phase-2/Later, never MVP-critical, and must never be a single point of failure for the judged demo.
- **No live vehicle telematics or autonomous dispatch integration** — this is strictly an offline decision-support tool, not a control system.
- **No cloud production deployment infrastructure** for the MVP — Docker Compose on the demo laptop is the deployment target, not a Kubernetes cluster or managed cloud service.

---

## 3. Target Users / Personas

**Persona 1 — The Enterprise Fleet Manager.** Operates a homogeneous delivery fleet (MVP scope) out of a single depot in a Tier-1 Indian metro. Daily workflow: upload a manifest of delivery nodes with demands, set vehicle capacity, run the optimizer, receive routes. Primary pain: fuel cost, SLA compliance, fleet under/over-utilization. This persona is the direct consumer of the **Green Impact dashboard** — liters of fuel saved, kg CO2 prevented, delta versus an unoptimized baseline, with underlying assumptions (fuel type, emission factor source) exposed in an assumptions modal so the numbers survive ESG-audit scrutiny rather than reading as an unsourced marketing claim.

**Persona 2 — The Municipal Traffic Analyst.** Cares about macroscopic, multi-agent load balancing across the city network, not any single fleet's P&L. The specific failure mode this persona needs mitigated: naive routing tools independently route every fleet onto the same "locally optimal" arterial, manufacturing a secondary bottleneck that did not exist before optimization. QPSO's probabilistic, diversity-preserving search (multiple near-equally-fit particles occupying *different* regions of solution space, versus classical PSO's tendency to collapse the whole swarm onto one trajectory) is the concrete mechanism this persona can exploit to test load-balancing scenarios — this should be demoed as a distinct scenario (multiple simulated fleets, one shared network) from the single-fleet Fleet Manager scenario, even though both reuse the same solver core.

---

## 4. Goals and Non-Goals

**Goals**
- Empirical, statistically defensible validation of QPSO vs. OR-Tools (multi-trial, seeded, reported with mean/σ/win-rate — not a single cherry-picked run).
- Accurate COPERT-based ecological quantification, with the Indian-emission-factor substitution explicitly sourced and flagged (Section 13), never left as an unsourced "adapted to Indian vehicle classes" claim.
- Live SSE convergence streaming that degrades gracefully (reconnect + replay) rather than failing silently.
- Fully offline execution — zero network dependency at demo time, including for the OSMnx graph fetch (pre-cached, Section 8).
- Explicit differentiation from existing public SIH26137 reference implementations via the ecological module, real Indian topology, and the three-tier benchmark methodology (Section 16, Section 20).

**Non-goals (MVP)**
- Cloud production deployment infrastructure.
- Live QPU integration of any kind.
- Live traffic API polling as a demo-critical dependency.
- Autonomous vehicle dispatch / hardware telematics integration.
- Multi-depot or heterogeneous-fleet support (explicitly deferred to V2/Phase 2 per baseline PRD).

---

## 5. User Stories

| As a... | I want... | So that... |
|---|---|---|
| Fleet Manager | to select an Indian city from a dropdown and have its real drivable street graph load | I plan routes against actual road topology, not an abstract graph |
| Fleet Manager | to upload a CSV of delivery nodes with demand/capacity fields | I define my daily CVRP scenario without manual data entry |
| Traffic Analyst | to inject a simulated accident onto a specific road edge and trigger re-optimization | I can observe how the algorithm responds to sudden disruption before trusting it live |
| Technical Evaluator | to watch a live convergence chart update via SSE during the solver run | I can visually verify QPSO is actually escaping local optima, not just reporting a static number |
| Technical Evaluator | to see QPSO and OR-Tools run against the identical distance matrix, seed, and time budget, with results shown side by side | I can trust the comparison is fair, not rigged by mismatched conditions |
| Fleet Manager | to view a Green Impact dashboard showing liters of fuel saved and kg CO2 prevented, with the emission-factor source stated | I can report a defensible number to ESG stakeholders, not an unsourced marketing figure |

---

## 6. Feature Scope

**MVP (SIH Prototype)**
Single depot, homogeneous fleet, CVRP (no time windows in the core MVP path — time windows are V2/VRPTW per baseline PRD roadmap). QPSO solver + OR-Tools baseline, run under identical seed/time-budget conditions (Section 7). OSMnx-derived real Indian city graph, pre-cached offline. SVRPBench-style log-normal stochastic delay injection. COPERT-based static ecological scoring. SSE-streamed live convergence. Before/after route map comparison. Green Impact dashboard with sourced assumptions modal. "How It Works" explainer modal for judges.

**V2**
Multi-depot (MDVRP). Heterogeneous EV/ICE fleets (COPERT fuel-type-dependent polynomials already scaffolded in the MVP data model — see Section 7's `Vehicle.fuel_type`). Time windows (VRPTW). OPQNN-based congestion prediction trained on historical data (e.g., New Delhi traffic datasets). Adaptive QEA operator scheduling via Q-learning (dynamically tuning the contraction-expansion coefficient `α` based on convergence stagnation, rather than the MVP's fixed non-linear decay schedule). TomTom Matrix API as an optional live-data toggle, never demo-critical.

**Later/Experimental**
QUBO formulation of the routing sub-problem. D-Wave Ocean SDK's `LeapHybridBQMSampler` (a hybrid classical/quantum-annealing solver, used only as a stretch exploration — not required, not installed by default). QAOA sub-routine offload for the clustering/Column-Generation pre-processing phase only (never the full CVRP). Zero-noise extrapolation (ZNE) / quantum signal processing (QSP) error mitigation, relevant only once actual QPU access is pursued.

---

## 7. Recommended Architecture

**DDD / Clean Architecture layering** (rationale: decouples the QPSO/OR-Tools mathematics from HTTP transport and from OSMnx's external-data volatility, so the algorithm layer is independently unit-testable and the transport layer can change — SSE today, WebSocket later — without touching solver code):

```
domain/entities/          Vehicle, Node, Route  — framework-agnostic business objects
domain/value_objects/     GeographicCoordinates, FitnessScore, CO2EmissionProfile — immutable
domain/exceptions.py      CapacityExceededError, TimeWindowViolation, GraphDisconnectedError
application/services/     OptimizationOrchestrator — coordinates concurrent QPSO + OR-Tools runs
application/interfaces/   Abstract repositories/solver ports (Dependency Inversion Principle)
infrastructure/algorithms/  qpso_solver.py, or_tools_baseline.py, copert_model.py
infrastructure/geospatial/  osmnx_client.py, distance_matrix_builder.py, stochastic_delay_injector.py
presentation/api/         FastAPI routers (job submission, status polling)
presentation/schemas/     Pydantic request/response models — strict boundary validation
presentation/sse/         Async generators yielding text/event-stream payloads
```

`OptimizationOrchestrator` in `application/services/` is the seam that enforces fairness-valid benchmarking (Section 7's directive below) — it owns the shared seed and shared time budget and hands both to the two solver adapters, so neither solver can be configured inconsistently by accident.

### Asynchronous execution — chosen approach and why

**Decision: `asyncio` background task + `ProcessPoolExecutor`, not Celery+Redis.**

Rationale: the QPSO solver is CPU-bound (Python loop with NumPy array math) and will hold the GIL if run naively inside an `async def` route handler — this blocks the FastAPI event loop, which also owns the SSE stream, so a naive implementation would freeze the very telemetry the demo exists to show. `run_in_executor` with a `ProcessPoolExecutor` moves the CPU-bound solve into a separate OS process, freeing the event loop to keep serving the SSE stream. A Celery+Redis (or RQ) queue would solve the same problem but adds a broker daemon as a new demo-day failure surface, a serialization boundary for job state, and operational complexity (worker process lifecycle, Redis persistence) with zero benefit for a single-laptop, single-concurrent-demo deployment target. Celery only earns its complexity when there is a need for horizontal worker scaling or job durability across process restarts — neither applies here.

**Trade-off stated explicitly:** the chosen approach is simpler to run and debug on one machine but does not survive an API-process restart mid-solve (the in-flight job is lost) and does not horizontally scale across machines. For an offline, single-demo-laptop MVP this is the correct trade — Celery's operational overhead is a demo-day liability, not a safety net, at this scale.

**Implementation sketch:**
```python
# application/services/optimization_orchestrator.py
import asyncio
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor(max_workers=2)  # one slot per concurrent solver

async def run_comparison(job_id: str, matrix, seed: int, time_budget_s: float):
    loop = asyncio.get_running_loop()
    convergence_cache[job_id] = []  # in-memory cache for SSE replay on reconnect
    try:
        qpso_future = loop.run_in_executor(
            executor, run_qpso_in_subprocess, matrix, seed, time_budget_s, job_id
        )
        ortools_future = loop.run_in_executor(
            executor, run_ortools_in_subprocess, matrix, seed, time_budget_s
        )
        qpso_result, ortools_result = await asyncio.gather(qpso_future, ortools_future)
        job_results[job_id] = {"qpso": qpso_result, "ortools": ortools_result, "status": "done"}
    except Exception as exc:
        job_results[job_id] = {"status": "error", "detail": str(exc)}
        await sse_broadcast(job_id, event="error", data={"message": str(exc)})
```
`run_qpso_in_subprocess` must periodically push partial convergence values into a multiprocessing-safe channel (a `multiprocessing.Manager().list()` or a simple polling of a shared file/queue) that the SSE generator reads from — this is the concrete mechanism by which the *other* process's progress reaches the event loop for streaming.

### Fairness-valid benchmarking — exact seeding and time-budget protocol

- **Single global seed**, generated once per run (e.g., `seed = secrets.randbits(32)` or a user-supplied override for reproducibility), logged in the `SimulationResult` record.
- Applied to QPSO via `rng = numpy.random.default_rng(seed)`, used for **every** stochastic draw in the algorithm: initial particle positions, the `φ ~ U(0,1)` attractor mix, the `u ~ U(0,1)` Monte Carlo draw, and the `±` sign coin-flip (Section 9). No `numpy.random` global-state calls — only draws from this one `Generator` instance, so the run is bit-for-bit reproducible given the same seed.
- Applied to OR-Tools: pass the same integer as `search_parameters.random_seed` if the installed OR-Tools version's `RoutingSearchParameters` exposes it (recent CP-SAT-backed versions do); if the specific routing API in use does not expose a settable seed, this must be logged explicitly as a **known limitation** in the results output ("OR-Tools seed: not configurable in this build — reporting mean/σ over N trials instead of relying on seed-matched determinism"), never silently ignored. **This is a correction to the baseline PRD's implicit assumption that seed-parity is automatic — it is not, and must be verified against the installed OR-Tools version before the fairness claim is presented to judges.**
- **Time budget parity, not just OR-Tools's timeout.** OR-Tools already accepts a hard wall-clock `time_limit` on its search parameters. QPSO's iteration loop must independently enforce the same wall-clock cutoff — not just an iteration count — via:
```python
start = time.monotonic()
for iteration in range(max_iterations):
    if time.monotonic() - start >= time_budget_s:
        break
    # ... QPSO update step ...
```
Without this explicit check, a "fair" comparison silently becomes "QPSO ran until convergence, OR-Tools ran until timeout" — an invalid comparison the baseline PRD's user story (`5-second hard timeout... to match the heuristic execution time`) correctly gestures at but does not specify how to enforce on the QPSO side. This loop is the specification that closes that gap.

### SSE streaming pipeline and exception handling

```python
# presentation/sse/convergence_stream.py
async def convergence_event_stream(job_id: str, request: Request):
    last_sent_index = 0
    while True:
        if await request.is_disconnected():
            break
        history = convergence_cache.get(job_id, [])
        for point in history[last_sent_index:]:
            yield f"event: progress\ndata: {json.dumps(point)}\n\n"
        last_sent_index = len(history)
        status = job_results.get(job_id, {}).get("status")
        if status == "error":
            yield f"event: error\ndata: {json.dumps(job_results[job_id])}\n\n"
            break
        if status == "done":
            yield f"event: complete\ndata: {json.dumps(job_results[job_id])}\n\n"
            break
        await asyncio.sleep(0.25)
```
The frontend `EventSource` must register a distinct handler for `event: error` (render an explicit failure banner, stop the spinner, offer a retry button) separate from its `event: progress` handler — an unhandled backend exception must never present as an infinitely spinning chart. On reconnect (browser-native `EventSource` retry, or an explicit exponential-backoff wrapper), the generator's `last_sent_index = 0` restart against the still-populated `convergence_cache[job_id]` is what enables full-history replay (Section 15).

---

## 8. Deployment & Offline Infrastructure

**Docker Compose, mandatory, two services minimum:** `backend` (FastAPI + Python solver stack, pinned base image e.g. `python:3.11-slim`) and `frontend` (React build served via Nginx or Vite preview, pinned Node build stage). "Works on my machine" is treated as a fatal demo-day risk specifically because OSMnx/OR-Tools/NetworkX version drift between a developer's laptop and the demo laptop can silently change graph-cleaning behavior or solver output — Compose with pinned images is the mitigation, not an optional nicety.

**Dependency pinning:** `requirements.txt` with fully locked versions (`osmnx==<pinned>`, `ortools==<pinned>`, `networkx==<pinned>`, `fastapi==<pinned>`, `numpy==<pinned>`) generated via `pip freeze` from the exact environment the team validates against, or equivalently a `poetry.lock`/`pyproject.toml` if Poetry is the team's workflow — either is acceptable, but the lock file (not a loose `>=` range) is what must ship, and the demo laptop must install from that exact lock file, not `pip install -U` on demo morning.

**OSMnx Overpass API failure risk — mandatory offline pre-fetch.** The Overpass API (OSMnx's live data source) is a public, rate-limited, sometimes-slow third-party service — completely unacceptable as a live dependency during judging. Mitigation, to be executed once during development (not at demo time):
```python
import osmnx as ox

G = ox.graph_from_place("Koramangala, Bengaluru, India", network_type="drive")
G = ox.truncate.largest_component(G, strongly=True)  # isolate largest strongly connected component
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)
ox.save_graphml(G, filepath="cache/bengaluru_koramangala.graphml")
```
Every target city/scenario the demo will use must be pre-fetched, cleaned, and serialized to `.graphml` **ahead of time**, then the running application loads exclusively via `ox.load_graphml(filepath)` — zero network dependency on Overpass at demo time. `.graphml` (plain XML-based, NetworkX-native) is preferred over a database for this MVP because it needs no server process and round-trips cleanly through `networkx`/`osmnx`.

**CORS configuration for local dev:**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```
This must be explicit and origin-scoped (not `allow_origins=["*"]` in the deployed Docker Compose config) so frontend-backend integration doesn't silently fail during development, and so the demo build isn't left with an overly permissive CORS policy by accident.

**OpenStreetMap ODbL attribution.** OSMnx's underlying data is OpenStreetMap, licensed under the Open Database License (ODbL) — the PPT's official "Research and References" slide, and any public-facing deployment, must name "© OpenStreetMap contributors" as a documented data source. This is a licensing obligation, not a stylistic nicety, and omitting it is a compliance gap on a slide judges may specifically check.

---

## 9. The Algorithmic Engine: QPSO Mathematical Rigor

QPSO is implemented as **pure classical mathematics** — no Qiskit, no Cirq, no quantum circuit simulator is required or should be installed for this component. It borrows quantum *probabilistic math* (probability-density-based sampling, delta-potential-well attractor mechanics), not quantum hardware simulation. Any actual QUBO/circuit-adjacent tooling (e.g., `dimod.SimulatedAnnealingSampler` from D-Wave's classical-mode Ocean SDK) is reserved **strictly** for the optional QIEA/operator-scheduling stretch variant in Section 6's "Later/Experimental" bucket — installing Qiskit/Cirq for the MVP's QPSO path is wasted setup effort and must be explicitly avoided.

**State representation — Rank-Order Value (ROV) mapping.** A particle's position is a continuous vector `X_i ∈ R^N` (N = number of customer nodes). To convert this into a valid CVRP permutation (a sequence containing every node exactly once), apply ROV: sort the N continuous values and use the resulting rank order as the discrete node-visit sequence. This guarantees, by construction, no duplicate and no missing node — the permutation validity is a structural property of the sort operation, not something the fitness function needs to check or penalize.

**Local attractor point.** For particle `i` at iteration `t`:
```
P_i(t) = φ · Pbest_i(t) + (1 − φ) · Gbest(t),   φ ~ U(0,1)
```
`φ` is redrawn independently per particle, per dimension, per iteration from the shared seeded RNG (Section 7).

**Mean best position ("mainstream thought").** Computed once per iteration across the entire swarm of `M` particles:
```
mbest(t) = (1/M) · Σ_i Pbest_i(t)
```

**Position update (Monte Carlo wavefunction-collapse simulation):**
```
X_i(t+1) = P_i(t) ± α · |mbest(t) − X_i(t)| · ln(1/u),   u ~ U(0,1)
```
The `±` sign is chosen with 50% probability per particle per dimension (a Bernoulli draw from the same seeded RNG). This is the step that gives QPSO its "tunneling" behavior — the `ln(1/u)` term has unbounded support as `u → 0`, meaning a nonzero (if shrinking) probability of a large jump exists at every iteration, which is exactly the mechanism classical PSO's bounded velocity update lacks and which lets the swarm escape a local optimum that traps classical PSO.

**Contraction-expansion coefficient (`α`) schedule.** `α` decreases non-linearly from 1.0 to 0.5 across the iteration budget — large `α` early (hyper-exploration, wide jumps) transitioning to small `α` late (aggressive local exploitation, fine-tuning around the current best). A standard non-linear schedule:
```python
alpha = 1.0 - (1.0 - 0.5) * (iteration / max_iterations) ** k   # k > 1 biases toward late-stage exploitation
```
`k` is a tunable hyperparameter (recommend `k = 1.5–2.0` as a starting point, to be validated empirically in Section 14's convergence testing).

### 9.1 QPSO vs. QAOA — explicit justification

QPSO is chosen over QAOA specifically because: (a) QPSO's computational cost scales with classical CPU cycles and memory for an `N`-dimensional continuous vector per particle, not with physical qubit count, so it does not hit NISQ hardware ceilings at 50–100 node scale; (b) QPSO has no variational-circuit parameter-optimization loop, so it cannot suffer a barren plateau — there is no vanishing-gradient failure mode in a classical Monte Carlo position update. QAOA, by contrast, would need its qubit count to scale at least quadratically with customer count to encode CVRP's capacity/uniqueness constraints as penalty terms, and its classical outer-loop optimizer is exactly the component barren plateaus break as circuit depth and problem density increase. This is the same justification given in Section 1, restated here at the point where the actual algorithm choice is made.

### 9.2 The industrial baseline: Google OR-Tools

`ortools.constraint_solver.pywrapcp` is the classical baseline. Configuration for a fair comparison: `first_solution_strategy = PATH_CHEAPEST_ARC` (fast, greedy initial feasible solution), `local_search_metaheuristic = GUIDED_LOCAL_SEARCH` (the metaheuristic layer that lets OR-Tools escape its own local optima — without this, the comparison would be QPSO vs. a plain greedy heuristic, not vs. OR-Tools's real capability), and `time_limit` set to the identical wall-clock budget enforced on QPSO (Section 7).

---

## 10. Geospatial Preprocessing Pipeline

1. **Ingestion:** `ox.graph_from_place("<Indian city/neighborhood>", network_type="drive")` — done once, offline, ahead of the demo (Section 8).
2. **Topology normalization:** retain only the **largest strongly connected component** (`ox.truncate.largest_component(G, strongly=True)`), discarding isolated nodes (gated communities, mapping errors, dead-end fragments with no routable exit). Without this step, an all-pairs shortest-path call will throw an infinite-distance/unreachable-node exception the moment a delivery node lands in a disconnected fragment.
3. **Node snapping:** delivery nodes supplied by CSV upload are lat/lon points that will rarely land exactly on a graph node. Snap each to its nearest valid, traversable edge using spatial indexing (`ox.distance.nearest_edges`, which is R-tree-backed internally) rather than nearest raw node, so a delivery point near a road (not at an intersection) is still correctly routable.
4. **Edge speed imputation:** `ox.add_edge_speeds(G)` — fills missing `maxspeed` tags using OSMnx's highway-type-conditioned default speed table (e.g., residential ≈30 km/h, primary/arterial ≈60 km/h), since raw OSM data frequently omits speed tags entirely.
5. **Travel time calculation:** `ox.add_edge_travel_times(G)` — derives a deterministic base travel time per edge from length and imputed speed.
6. **Distance/time matrix generation:** compute the all-pairs shortest path (Dijkstra, via `networkx.multi_source_dijkstra` or OSMnx's shortest-path helpers) restricted to the delivery-node subset, producing an `N×N` **asymmetric** travel-time matrix (asymmetric because one-way streets and differing uphill/downhill or turn-restriction paths make `time(a→b) ≠ time(b→a)` in a real road network — the baseline PRD's own data model correctly reflects this via `EdgeWeight`'s directional fields).
7. **Stochastic delay injection (SVRPBench-modeled):** multiply each base travel time by a log-normal random multiplier, per the SVRPBench formulation (Section 2.1 of that paper): baseline free-flow parameters `μ_base = 0`, `σ_base = 0.3`, with peak-hour amplification terms `δ = 0.1`, `ε = 0.2` layered on top of a Gaussian time-of-day congestion factor (morning/evening peaks at `μ = 8`/`17` hours, `σ = 1.5`). This is drawn from the same seeded RNG as the solver (Section 7), so a given seed reproduces an identical stochastic traffic realization across both QPSO and OR-Tools runs — essential for the comparison to be about *algorithm* quality, not about which algorithm happened to get an easier random traffic draw.

---

## 11. Mathematical Normalization Techniques

**Multi-objective fitness normalization.** Distance (meters, e.g. ~50,000), time (seconds, e.g. ~3,600), and CO2 (kilograms, e.g. ~12) differ by orders of magnitude. Left unnormalized, the fitness function is dominated entirely by whichever objective has the largest raw magnitude — in practice, distance would mathematically drown out the ecological objective the sponsor cares most about. Mandatory: Min-Max normalization of every objective to `[0,1]` **before** applying scalar preference weights:
```
obj_norm = (obj_raw − obj_min_observed) / (obj_max_observed − obj_min_observed)
fitness = w_distance · dist_norm + w_time · time_norm + w_co2 · co2_norm
```
`obj_min_observed`/`obj_max_observed` should be tracked per-run across the current population/swarm (not a fixed global constant), since the practically achievable range of each objective depends on the specific problem instance's scale.

**QIEA L2 normalization constraint (only if the QIEA stretch variant is built).** After every application of the quantum rotation gate `U(Δθ)` to a Q-bit pair `(α, β)`, the constraint `α² + β² = 1` must be re-verified (or re-normalized: `α, β ← α/√(α²+β²), β/√(α²+β²)`) — a rotation gate is mathematically norm-preserving in exact arithmetic, but floating-point accumulation error across many iterations can drift the pair away from a valid probability amplitude, which would make the subsequent measurement step (`bit = 1 if r < β² else 0`) statistically invalid. This is verified as a property-based test in Section 14, not just asserted here.

---

## 12. Precision-Recall Trade-off in Stochastic Routing

**Precision-first (conservative) routing** never violates capacity or time-window constraints, at the cost of fleet under-utilization — more vehicles than strictly necessary, higher operational cost, because the solver leaves capacity headroom to absorb any possible stochastic delay. **Recall-first (aggressive) routing** packs vehicles tightly for maximum theoretical efficiency, accepting the risk that a realized delay forces an expensive mid-route depot return when a capacity or time-window violation actually occurs.

Classical solvers (OR-Tools included) typically resolve this via **rigid hard constraints** — a route exceeding capacity by even a fraction is instantly invalid and discarded from consideration, which forces the solver toward the conservative end of the spectrum by construction. QPSO instead uses a **dynamic, scaling penalty function** `λ`: an infeasible route is not discarded but assigned a severe fitness penalty proportional to the *magnitude* of the violation, e.g. `penalty = λ · max(0, load − capacity)^2` (squared to punish larger violations disproportionately more than small ones). This creates a "soft wall" in the fitness landscape rather than a hard cliff — the swarm can mathematically pass *through* a temporarily-penalized, technically-infeasible region of the search space (because the position-update math in Section 9 does not check feasibility before moving) to discover a tighter, fully-feasible optimum that a hard-constraint solver would never explore because it prunes that region outright. `λ` itself should scale up as the run progresses (small early, to permit exploration; large late, to force final convergence toward strictly feasible solutions) — a schedule symmetric in spirit to the `α` decay in Section 9.

---

## 13. Ecological Metrics (COPERT Integration)

**Non-linear speed-emissions relationship.** COPERT IV models emissions as a polynomial function of average speed, not a flat per-km constant, because real vehicle emissions spike at low speed (prolonged idling/stop-start driving in congestion), dip to a minimum in an efficient cruise band (~40–60 km/h), and rise again at high speed (aerodynamic drag dominates fuel consumption). A representative COPERT-style polynomial form:
```
EF(v) = (a + b·v + c·v²) / v   [g/km, per COPERT IV functional form, coefficients vary by vehicle/fuel class]
```
where `a, b, c` are fuel/vehicle-class-specific coefficients published in COPERT IV documentation.

**Indian vehicle-class emission-factor source — explicitly named, not left unsourced.** Per the research finding in Section "(2)" above, no authoritative India-specific emission-factor dataset with COPERT's level of rigor was located. **Flagged assumption, stated explicitly rather than silently glossed over:** this platform will use **COPERT IV's published speed-dependent polynomial *shape*** (the non-linear curve behavior — idling spike, cruise-band minimum, highway-drag rise — which is a function of vehicle physics, not geography, and is therefore geography-independent) combined with **base emission-factor magnitudes proxied from IPCC 2019 Refinement default road-transport emission factors** (kg CO2 per liter of fuel, by fuel type — internationally standardized, publicly documented, and explicitly designed as a default for jurisdictions lacking a national inventory) as the closest available authoritative proxy for Indian vehicle classes, until/unless the team locates and substitutes ARAI (Automotive Research Association of India) or CPCB (Central Pollution Control Board) published factors. This substitution — COPERT curve shape × IPCC default magnitude — must be stated on-screen in the assumptions modal (per Persona 1's user story, Section 5) exactly as described here, not presented as a precise India-specific figure.

**Fitness-function integration.** The QPSO fitness function queries `EF(v)` for the average speed of each edge in a candidate route (using the OSMnx-imputed edge speed from Section 10, adjusted by whatever stochastic delay multiplier was drawn for that trial) and adds the resulting CO2 estimate as a weighted, Min-Max-normalized term (Section 11) to the overall fitness. This actively steers the swarm away from routes that pass through low-speed, high-congestion edges — not because distance is penalized, but because the *emissions* term specifically spikes on those edges, which is the mechanism that produces genuinely different (not just shorter) routes than a pure distance-minimizing baseline, and is the concrete, demoable proof of the "green corridor" claim.

---

## 14. Concurrency, Testing & Validation Strategy

| Test category | What it verifies |
|---|---|
| Unit tests | COPERT polynomial output against known reference values (hand-computed or literature-sourced fixed points) for at least three speed bands (idle, cruise, highway) |
| Property-based tests (Hypothesis or equivalent) | ROV mapping, for any input vector of length N, always produces a permutation of `{0, ..., N-1}` with no duplicates and no omissions |
| Property-based tests | QIEA rotation-gate application, for any starting valid `(α, β)`, always yields `α² + β² = 1` (within floating-point tolerance) after the gate is applied — run for many random starting states and many rotation angles |
| Load/soak tests | SSE stream under simulated connection drops (kill the client mid-stream, reconnect after N seconds, assert full `convergence_history` replay arrives and no gap exists) |
| Integration tests | Concurrent solver requests (fire 2+ simultaneous `/optimize` calls) do not block the FastAPI event loop — assert a lightweight `/health` endpoint remains responsive with sub-100ms latency throughout a concurrent solver run |

**Empirical success metrics (carried forward unchanged from the baseline PRD — these are the authoritative targets, not renegotiated here):**
- ≥65% QPSO win rate vs. OR-Tools on 50–100 node networks, across randomized head-to-head trials.
- <1.0% mean optimality gap vs. exact dynamic-programming ground truth on N=15 instances.
- 95% Gbest convergence within T/3 iterations vs. classical PSO.
- ≥10% CO2 reduction vs. an unoptimized nearest-neighbor baseline.
- <15 second end-to-end demo latency for a standard 50-node problem.

All benchmark runs that produce these numbers must log: seed, time budget, OR-Tools version and configured seed-capability status (per Section 7's caveat), node count, and city/topology used — every reported number must be reproducible from this log alone.

---

## 15. Error Analysis and Failure States

- **Topological disconnection:** handled structurally by strongly-connected-component isolation and node snapping (Section 10) — this must happen at ingestion time, not be caught as a runtime exception during solving.
- **Algorithm stagnation:** if `Gbest` fails to improve by ≥0.01% for 50 consecutive iterations, vaporize and randomly re-initialize the worst-performing 20% of the swarm (ranked by personal-best fitness), forcing renewed exploration. This is a concrete, testable trigger condition — implement it as an explicit counter reset on any improving iteration, not an approximate heuristic.
- **SSE network drop recovery:** frontend implements exponential-backoff reconnection (native `EventSource` retry behavior, or a thin wrapper enforcing a max backoff ceiling); backend caches the full `convergence_history` in memory per job and replays it from index 0 on any new connection to that job's stream (Section 7's SSE sketch) — the UI rebuilds the chart from the replayed history rather than resuming from a broken mid-point, so no data point is ever silently lost from the judge's view.
- **Solver-task crash handling:** any unhandled exception inside the background solver task must be caught at the orchestrator boundary (Section 7's `try/except` around `asyncio.gather`) and broadcast as an explicit `event: error` SSE payload; the frontend must render a clear failure state (banner + retry action), never an infinitely spinning chart.
- **Stochastic demand failures:** objective-function penalty weights (`λ` from Section 12, the normalization bounds from Section 11) must be hot-swappable mid-execution — i.e., the orchestrator exposes a method to update penalty parameters on a running or subsequent job without a full service restart — laying groundwork for the V2 capability of re-optimizing only the unfulfilled nodes after a mid-route demand-exceeds-forecast event, without requiring that full re-optimization feature to exist in the MVP itself.

---

## 16. Live Demo Contingency Planning

Because the target win rate is ≥65% — meaning up to roughly 35% of live trials could see QPSO underperform OR-Tools — the live judging demo must not rely on an un-rehearsed, freshly-random trial:

- **Rehearsal requirement, not an afterthought.** During development, run many head-to-head trials across multiple city/node-count/seed combinations and **record which specific combination reliably favors QPSO** under the exact wall-clock-fair conditions specified in Section 7. This combination becomes the **primary demo scenario** — documented explicitly (city name, node count, seed value, expected QPSO/OR-Tools tour-length delta) in the team's internal demo runbook.
- **Live judge-supplied input, framed honestly.** Per the demo-mechanics research finding, letting a judge supply part of the input scenario live (e.g., picking delivery nodes on the map) is a stronger demo than a fully pre-scripted run — but this must be layered *on top of* the rehearsed primary scenario's known-good topology/seed, not run against a completely fresh random seed the team has never tested.
- **Secondary backup: a pre-recorded run.** Keep a screen recording (60–90 seconds) of a full successful run — including the SSE convergence chart animating and the Green Impact dashboard populating — as the explicit fallback if the live laptop, Docker stack, or Wi-Fi (for anything unexpectedly network-dependent) fails during judging. This is not a substitute for a live demo attempt; it is the named fallback if the live attempt visibly breaks.
- **No screen ever empty.** Seed the application with the primary demo scenario's data pre-loaded by default, so a judge arriving mid-session or a nervous reset never lands on a blank state.

---

## 17. Security & Payload Limits

- **CSV upload size limit:** reject any upload exceeding a defined threshold (e.g., 5 MB) at the raw-bytes level, **before** the payload reaches Pydantic parsing — a memory-exhaustion attempt via a maliciously huge CSV must be rejected at the transport boundary (check `Content-Length` header / stream size cap), not after being fully buffered into memory for validation.
- **Strict Pydantic schema validation** on every API boundary (node coordinates within plausible lat/lon bounds, demand ≥0, capacity >0, no unexpected extra fields via `model_config = ConfigDict(extra="forbid")`) — this is the domain-boundary defense the DDD layering (Section 7) is specifically structured to enforce at `presentation/schemas/`.
- **OSMnx bounding-box size limits:** the offline cache-generation step (Section 8) must sanity-check the requested place/bounding-box area before calling `ox.graph_from_place` — an accidental pan-India-scale query would hang the Overpass fetch or exhaust local memory during graph cleaning; cap the accepted place query to a single named city/district-scale area, and reject or warn on anything larger, at cache-generation time (not at demo time, since this pipeline never runs live during judging per Section 8).

---

## 18. Folder Structure

```
app/
├── domain/
│   ├── entities/
│   │   ├── vehicle.py
│   │   ├── node.py
│   │   └── route.py
│   ├── value_objects/
│   │   ├── geographic_coordinates.py
│   │   ├── fitness_score.py
│   │   └── co2_emission_profile.py
│   └── exceptions.py
├── application/
│   ├── services/
│   │   └── optimization_orchestrator.py
│   └── interfaces/
│       ├── solver_port.py
│       └── geospatial_repository_port.py
├── infrastructure/
│   ├── algorithms/
│   │   ├── qpso_solver.py
│   │   ├── or_tools_baseline.py
│   │   └── copert_model.py
│   └── geospatial/
│       ├── osmnx_client.py
│       ├── distance_matrix_builder.py
│       └── stochastic_delay_injector.py
└── presentation/
    ├── api/
    │   └── v1/
    │       ├── optimize_router.py
    │       └── scenario_router.py
    ├── schemas/
    │   ├── optimize_request.py
    │   └── optimize_response.py
    └── sse/
        └── convergence_stream.py

cache/                       # pre-fetched .graphml files, zero live Overpass dependency
tests/
├── unit/
├── property_based/
└── integration/
docker-compose.yml
backend/requirements.txt      # or pyproject.toml + poetry.lock
frontend/                     # React + TypeScript
```

---

## 19. Roadmap

**Phase 1 — SIH Prototype (~6-month roadmap narrative; actual build window per Section 0's flagged timeline conflict):** CVRP + QPSO + OR-Tools baseline + OSMnx (offline-cached) + SSE + static COPERT (IPCC-magnitude-proxied, per Section 13).

**Phase 2 — Years 1–2:** MDVRP, heterogeneous EV/ICE fleets, VRPTW, OPQNN-based congestion prediction (trained on historical datasets, e.g. New Delhi traffic data), adaptive QEA operator scheduling via Q-learning (dynamically tuning `α`/rotation-angle schedules based on live convergence stagnation rather than the MVP's fixed decay curve), TomTom Matrix API as an optional live-data fallback.

**Phase 3 — Years 3–5:** QUBO formulation of the routing sub-problem; D-Wave Ocean SDK's `LeapHybridBQMSampler` for offloading constrained sub-problems (e.g., macroscopic load-balancing across a large urban grid) to hybrid classical/quantum-annealing hardware as it matures; a QAOA evaluation pipeline restricted to sub-routine offload (e.g., Column-Generation clustering) rather than full CVRP; zero-noise extrapolation (ZNE) and quantum signal processing (QSP) error mitigation once genuine QPU access is pursued.

---

## 20. SIH Judging Criteria Alignment

| SIH criterion | How this blueprint's decisions support it |
|---|---|
| **Novelty** | Three-tier benchmark methodology (exact ground truth → OR-Tools → QPSO) plus the COPERT/Egreen ecological module — the single differentiator research confirms is absent from known competing SIH26137 implementations |
| **Complexity** | Full QPSO mathematical rigor (ROV mapping, delta-potential attractor, mean-best-position, Monte Carlo wavefunction-collapse update, adaptive `α` schedule) implemented and property-tested, not asserted |
| **Clarity / format compliance** | "How It Works" explainer modal (Section 5); explicit OSM ODbL attribution slide (Section 8); assumptions modal naming the exact emission-factor proxy (Section 13) rather than an unsourced figure |
| **Feasibility** | Fully offline execution (pre-cached `.graphml`, no live API dependency), Docker Compose pinned-image parity, asyncio+ProcessPoolExecutor chosen specifically for single-laptop demo reliability over Celery's operational overhead |
| **Practicability** | Seeded, wall-clock-fair, multi-trial benchmarking (mean/σ/win-rate) rather than a single cherry-picked run — the kind of rigor a technically literate judge specifically checks for |
| **Sustainability** | COPERT-based CO2/fuel quantification directly answers the sponsor's own "Egreen Quanta" branding and its sibling problem statement's (SIH26138) fuel/green-fleet theme |
| **Scale of impact** | Municipal Traffic Analyst persona's multi-agent load-balancing scenario demonstrates systemic (not just single-fleet) impact potential |
| **User experience** | Live SSE convergence chart with explicit error-state handling (never an infinite spinner); before/after route map comparison; Green Impact dashboard |
| **Future work progression** | Explicit 3-phase, 5-year roadmap (V2 MDVRP/VRPTW/OPQNN/Q-learning; Later QUBO/D-Wave/QAOA/ZNE) shows a credible technology-maturity-aware progression rather than a one-off prototype |

---

## 21. Final Architecture & Library Decisions

**Backend:** Python + **FastAPI** (async-native, required for concurrent SSE + background solver execution). **OSMnx** for geospatial ingestion (offline pre-cached `.graphml`, Section 8). **OR-Tools** (`ortools.constraint_solver.pywrapcp`) as the classical baseline. **NumPy** for all QPSO Monte Carlo math, driven by a single seeded `numpy.random.Generator`. **NetworkX** (OSMnx's underlying graph library) for shortest-path/all-pairs computation. No Qiskit/Cirq/quantum-simulator dependency anywhere in the MVP path (Section 9). `dimod`/D-Wave Ocean SDK (classical-mode only) reserved strictly for the optional Later/Experimental QIEA stretch — not installed for MVP.

**Frontend:** **React + TypeScript** for type safety across the API boundary. **Deck.GL** for WebGL-accelerated route-map rendering (handles thousands of edges without degradation — needed once the demo scales past a toy node count). **Recharts** for the live SSE-driven convergence chart.

**Containerization:** **Docker Compose**, two pinned-base-image services (`backend`, `frontend`), locked dependency files (`requirements.txt` or `poetry.lock`) — no `latest` tags anywhere in the Compose file.

**Concurrency model:** `asyncio` background tasks + `ProcessPoolExecutor` (Section 7) — not Celery+Redis, for the stated single-laptop-demo trade-off reasons.

**Build order for Week 1 (dependency-ordered checklist, valid regardless of actual calendar time available — see Section 0's timeline flag):**
1. Stand up the DDD folder skeleton (Section 18) and a minimal FastAPI app with the CORS middleware (Section 8) and a `/health` endpoint — verify Docker Compose brings both services up together before writing any solver code.
2. Pre-fetch and cache one target city's `.graphml` (Section 8) and validate the largest-strongly-connected-component + edge-speed/travel-time pipeline (Section 10) against it end-to-end in a standalone script, before wiring it into the API.
3. Implement `or_tools_baseline.py` first (Section 9.2) — it is the smaller, better-documented, more mechanically-defined piece, and gives the team an immediate working route-comparison baseline to validate the distance-matrix pipeline against.
4. Implement `qpso_solver.py` (Section 9) against the same distance matrix, starting with the ROV mapping and position-update math validated via the property-based tests in Section 14 *before* wiring it into the orchestrator — a solver whose permutation-validity property is unverified is not safe to benchmark.
5. Wire `optimization_orchestrator.py`'s seeded, time-budget-matched concurrent execution (Section 7) and the SSE stream with explicit error-event handling (Section 7, Section 15) — this is the piece that turns two working standalone solvers into the actual judged demo capability.
6. Add `copert_model.py` (Section 13) and the Green Impact dashboard last among backend pieces — it is additive to an already-working distance/time comparison, not a blocker for validating the core algorithmic claim.
7. In parallel (not sequential — a second team member can start this once the API contract in `presentation/schemas/` is fixed in step 1): build the React map view, convergence chart, and results dashboard against a mocked/stubbed API response, then swap to the live SSE stream once step 5 lands.
