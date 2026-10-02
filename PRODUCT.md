# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React 19 + TypeScript + Vite (existing scaffold at `frontend/`). Deck.GL for WebGL route-map rendering, Recharts for the live SSE-driven convergence chart — both named explicitly in `SIH26137_Implementation_PRD.md` Section 21, not a free choice. Backend: FastAPI (Python), already exposes `POST /jobs` (raw distance/time-matrix payload) and `GET /jobs/{id}/stream` (SSE convergence events) — both currently temporary/unvalidated wiring per `backend/app/main.py`'s own comments, real Pydantic-validated routers deferred to a later phase.

## Users

Three personas, per `docs/planning/SIH26137_Implementation_PRD.md` Section 5:
- **Enterprise Fleet Manager** — uploads a delivery-node CSV, configures vehicle capacity, runs the optimizer, reads the results/green-impact comparison.
- **Municipal Traffic Analyst** — injects a simulated road-accident/delay and observes how both solvers re-route around it.
- **Technical Evaluator (SIH judge)** — watches the live convergence chart, inspects the QPSO math and fairness/reproducibility footer (seed, time budget, solver versions), reads the benchmark numbers. Judges have **under 2 minutes per screen** — this is a hard legibility constraint, not a nice-to-have.

## Product Purpose

A CVRP (capacitated vehicle routing problem) route optimizer that runs a quantum-inspired swarm algorithm (QPSO) head-to-head against a classical baseline (Google OR-Tools), on real Indian city road graphs (OSMnx-derived, offline-cached), under stochastic traffic-delay conditions (SVRPBench-modeled), and reports the resulting route quality and CO2/fuel/time savings. Success = a judge or fleet manager can see, without reading prose, which algorithm won and by how much, and can verify every number's source on demand.

## Positioning

Per the PRD's own competitive research: multiple existing public QPSO/QIEA-for-VRP prototypes exist, but the most advanced reference implementation found does **not** implement ecological/green metrics despite green-fleet optimization being the sibling problem statement's explicit focus. This product's differentiation is the combination other teams didn't ship: real Indian road topology + stochastic delay + a sourced (not invented) CO2/fuel/time comparison + fairness-transparent (seeded, time-budget-matched) benchmarking — never sci-fi "quantum swirl" visual tropes, which the PRD explicitly flags as undercutting the mathematical-rigor claim.

## Operating Context

Runs on a single demo laptop (8–16GB RAM, no GPU) during a live judged demo, fully offline (no paid live-traffic APIs, no network dependency at runtime beyond the app's own frontend/backend). One pre-cached city graph currently exists: Indiranagar, Bengaluru (`backend/cache/indiranagar_bengaluru.graphml`) — the city picker is data-driven from a small list, not hardcoded to assume only one entry forever, but only one entry is real today. A pre-seeded default scenario must always be loadable so no screen is ever empty during the demo (PRD Section 16).

## Capabilities and Constraints

- Single depot, homogeneous fleet, CVRP only (no time windows) — PRD Section 6 MVP scope.
- Two algorithms only: OR-Tools (classical baseline, blue) and QPSO (quantum-inspired, amber/dashed) — PRD's fixed color/pattern encoding, colorblind-safe (blue/orange), must be identical across every screen (map, chart, table, stat card).
- CO2 figures use the COPERT curve-shape × IPCC-magnitude proxy (`backend/app/infrastructure/algorithms/copert_model.py`) — European-fleet-calibrated, explicitly flagged as not India-specific. Every CO2/fuel/time-saved number must have a one-tap path to this assumption; the primary reported metric is the **relative %** reduction, not the absolute kg figure.
- **Undecided / open at time of writing:** the real HTTP surface for turning "city selection + CSV upload" into a solver job (matrix-building from raw coordinates) does not exist yet as a validated endpoint — `backend/app/presentation/schemas/` and `optimize_router.py`/`scenario_router.py` are explicit stubs reserved for a later phase. Whether the frontend build gets a minimal bridging endpoint now or works against the existing raw-matrix `/jobs` payload with a pre-built demo scenario is a build-time decision, not decided here.
- Road-accident injection (Flow C, PRD/Design Brief) requires exposing individual graph edges for click-selection — no such endpoint exists yet either; scope for this build is an open decision, not assumed complete.
- Light mode is explicitly out of scope (Design Brief Section 3.1) — one dark theme only, to reduce demo-day QA surface.

## Brand Commitments

No existing brand name/logo beyond "SIH26137 — Quantum-Inspired Traffic Route Optimization." Visual mood is fixed by the Design Brief (Section 2): "engineering console, not consumer app" — references named are QGIS/Mapbox Studio (map-first layout), Grafana/Datadog (dense stat tiles, monospace numerals), Flightradar24/project44/FourKites (live line-on-map + side panel pattern), Palantir Foundry dark operational console. Explicitly avoid: purple/violet gradients, glowing particle/neural-net/holographic "quantum swirl" motifs, rounded bubbly consumer-SaaS cards, illustrated/cartoon empty states, decorative rainbow color use.

## Evidence on Hand

- `docs/planning/SIH26137_Design_Brief.md` — full token system (color/type/spacing/radius/shadow), 5-screen inventory, 3 user flows, per-screen layout hierarchy, component list.
- `docs/planning/SIH26137_Implementation_PRD.md` — architecture, algorithm math, API sketch, tech stack decision, testing strategy, roadmap.
- `EXPLAINABILITY.md` — running log of what's built, verified, and why, through Phase 5 (backend: geospatial pipeline, OR-Tools baseline, QPSO solver, COPERT emissions, async execution + SSE streaming — all complete and tested).
- No screenshots, logos, or other binary brand assets on hand.

## Product Principles

1. **The comparison is the hero, never a single algorithm shown alone** — every primary screen's dominant element is a side-by-side delta (Design Brief P1).
2. **Color encodes exactly one thing: which algorithm** — fixed blue/orange (+ solid/dashed redundant encoding), identical everywhere, never repurposed (Design Brief P2).
3. **Every number states its own assumption** — one tap/hover from any CO2/fuel/time figure to its source formula (Design Brief P3).
4. **Never fake a live signal** — an unhandled backend error must render an explicit failure state, never an infinitely spinning chart (PRD Section 15).
5. **Real data density over empty/illustrated states** — the pre-seeded demo scenario means no screen is ever actually empty.

## Accessibility & Inclusion

Colorblind-safe palette mandatory (deuteranopia/protanopia-safe blue/orange pairing), and color must never be the only encoding — line style (solid vs. dashed) is the redundant channel for the two route colors specifically (Design Brief Section 3.1). No other accessibility standard (e.g. WCAG level) was specified by the user or PRD.
