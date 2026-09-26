# SIH26137 — Design Brief
## Quantum-Inspired Traffic Route Optimization — UI/UX Blueprint (pre-code)
**Source of truth:** `SIH26137_Implementation_PRD.md` (features/architecture authoritative; this brief does not add scope, only form)
**Hard constraint:** every screen must be legible to a judge in under 2 minutes, on a laptop, in a 36-hour finale build window.

---

## 0. Ambiguities Flagged (not invented, not silently resolved)

- PRD does not specify vehicle count per route visually (icons vs. line-only). This brief assumes **line-only routes, no vehicle icons**, to keep build scope inside 36 hours — icons are a V2 nicety, not a judging-legibility requirement.
- PRD's CSV upload schema (exact column names) is not defined. This brief assumes a fixed template (`node_id, lat, lon, demand`) with a downloadable template link on the upload screen — needed for the flow to be demoable, not specified elsewhere.
- PRD does not say whether the "traffic accident injection" tool needs a full drawing UI or a simpler "click an edge" interaction. This brief assumes **click-an-edge-on-the-map**, not freehand drawing, since freehand drawing is unjustified build cost for a 36-hour window and the PRD's own acceptance criteria only require "select a road edge."

---

## 1. Design Principles

**P1 — The comparison, not the algorithm, is the hero.** Every primary screen's dominant visual element must be a *side-by-side delta* (route vs. route, number vs. number, curve vs. curve) — never a single algorithm's output shown alone. A judge with 90 seconds does not read prose; they read a delta. *Judging tie-in: this is the direct answer to "clarity" and "technical approach" — the deck's own strongest visual (per the PRD's research findings) is a before/after map with numbers on it, and this principle makes that the UI's default state, not a special screen.*

**P2 — Color encodes exactly one thing: which algorithm.** Classical-baseline and quantum-inspired outputs get one fixed color each, used identically everywhere (map lines, chart lines, table row accents, stat-card borders) — never repurposed for anything else (no using the "quantum" color for a generic success state elsewhere). A judge should be able to tell which number belongs to which algorithm without reading a legend, by the third screen. *Judging tie-in: this is what makes the QPSO-vs-classical comparison instantly legible without requiring the judge to already understand QPSO.*

**P3 — Every number on screen states its own assumption.** No CO2/fuel/time-saved figure appears without a one-tap/one-hover path to the exact formula or factor that produced it (the COPERT-proxy assumptions modal, the seed/time-budget log). This is a deliberate anti-"AI dashboard" move — vague, unsourced numbers are what every competing team's demo *doesn't* protect against, per the PRD's own competitive research. *Judging tie-in: practicability and feasibility — a technically literate judge who pokes at a number should find a source, not a shrug.*

---

## 2. Visual Direction

**Mood:** engineering console, not consumer app. Think of the screen as instrumentation for a real optimization run, not a marketing surface. Confidence comes from density and precision, not decoration.

**References (why each, specifically):**
- **QGIS / Mapbox Studio** — map-first layout convention: the map is the largest, most persistent element on screen, chrome recedes around it. This directly supports P1 (the comparison lives on the map).
- **Grafana / Datadog dashboards** — dense stat tiles, monospace numerals, sparklines-as-context — the visual grammar for "this number is measured, not decorative."
- **Flight-tracking tools (Flightradar24) / logistics ops platforms (project44, FourKites)** — real-time line-on-map with a live-updating side panel is structurally the same interaction pattern this product needs for the Live Optimization Run screen; reuse it rather than inventing a new pattern.
- **Palantir Foundry's dark operational-console mode** — precedent for a serious, technical dark theme that doesn't read as "gamer RGB."

**Explicitly avoid:**
- Purple/violet gradients, glowing particle/neural-net imagery, holographic or "quantum swirl" motifs anywhere. The differentiation angle *is* mathematical rigor and real Indian road data — sci-fi visual tropes actively undercut that claim by making the product look like every other "quantum-inspired VRP" submission the PRD's own research found already exists.
- Rounded, bubbly, consumer-SaaS card shapes with large drop shadows. This is a decision-support tool for a fleet manager and a traffic analyst, not a lifestyle app.
- Illustrated/cartoon empty-states. Use real data density instead (a pre-seeded default scenario, per PRD Section 16 — no screen is ever actually empty in the demo).
- Color used decoratively (rainbow chart palettes, gradient buttons). Every color on screen must be traceable to a token with a stated meaning (Section 3).

---

## 3. Design Tokens

### 3.1 Color

| Token | Hex | Usage | Why |
|---|---|---|---|
| `route-classical` | `#2E6BE6` (blue) | OR-Tools route line, its stat-card left border, its table-row accent, its chart line | Blue reads as "baseline/reference" cross-culturally in mapping tools |
| `route-quantum` | `#E8871E` (amber/orange) | QPSO route line, its stat-card left border, its table-row accent, its chart line | Blue/orange is a standard colorblind-safe pair (safe for deuteranopia and protanopia, the two most common forms) — the PRD explicitly requires this pairing to survive colorblind judges |
| `route-classical-pattern` | solid line, no dash | Redundant encoding for `route-classical` | Colorblind safety must not depend on color alone — line style is the backup channel if a judge's display or projector shifts hue |
| `route-quantum-pattern` | dashed line (6px/4px) | Redundant encoding for `route-quantum` | Same reasoning |
| `bg-canvas` | `#12161C` (near-black, dark mode default) | App background | Lets map + chart colors read with maximum contrast; matches the "operational console" mood |
| `bg-surface` | `#1B212B` | Panels, cards, modals | One step up from canvas — standard elevation via lightness, not shadow |
| `bg-surface-raised` | `#232B38` | Hovered/active card state | — |
| `border-subtle` | `#2E3742` | Card borders, dividers | Low-contrast structural lines, not decorative |
| `text-primary` | `#EDEFF2` | Headlines, primary numbers | — |
| `text-secondary` | `#9AA5B1` | Labels, captions, assumption footnotes | — |
| `accent-eco` | `#2FBF71` (green) | **Reserved exclusively for the Green Impact dashboard's positive-delta figures** — never used for route lines | Per P2: color encodes one thing per context; green here means "environmental saving," and must never collide with a route color |
| `status-error` | `#E5484D` | Error banners, solver-crash state, disconnected SSE indicator | Standard, unambiguous "something broke" red — the one place a saturated red is intentional |
| `status-warning` | `#F2C94C` | "City not cached" state, assumption caveats | — |
| `status-live` | `#2FBF71` | "Solver running" pulse indicator | Reuses the eco green deliberately for "actively good/working" states outside the eco dashboard's numeric figures specifically — acceptable because it's a status dot, not a data-encoding color, so it doesn't violate P2 |

*Light mode is out of scope for the 36-hour build — the demo runs on one controlled laptop/projector, and a single dark theme reduces both design and QA surface area. Flagged here as a deliberate scope cut, not an oversight.*

### 3.2 Type

Two families only:
- **UI/body:** Inter (or system-ui fallback) — clean, high legibility at small sizes, free.
- **Numerals/data/technical labels:** IBM Plex Mono — every stat-card figure, table cell number, chart axis label, and the QPSO formula block in the "How It Works" modal uses this. Monospace numerals signal "measured instrument reading," reinforcing P3 and the engineering-tool mood.

| Token | Size / line-height | Usage |
|---|---|---|
| `text-display` | 32px / 40px, Inter Semibold | Screen titles only (5 total in the app) |
| `text-h2` | 20px / 28px, Inter Semibold | Section headers within a screen |
| `text-body` | 14px / 20px, Inter Regular | Labels, descriptions, modal body text |
| `text-caption` | 12px / 16px, Inter Regular, `text-secondary` | Assumption footnotes, timestamps |
| `text-stat-lg` | 28px / 32px, IBM Plex Mono Semibold | Primary stat-card figures (CO2 saved, tour length) |
| `text-stat-sm` | 16px / 20px, IBM Plex Mono Regular | Table cells, chart axes |

### 3.3 Spacing, radius, shadow

- **Spacing scale:** 4px base unit — `4, 8, 12, 16, 24, 32, 48, 64`. No arbitrary values; every margin/padding in the component library must map to one of these.
- **Radius:** `4px` (inputs, small chips), `6px` (cards, buttons), `8px` (modals). Deliberately small and consistent — nothing above 8px — to keep the "engineering tool" read; large 16–24px radii are a consumer-app tell this brief explicitly avoids.
- **Shadow:** elevation is conveyed by **background lightness step** (`bg-canvas` → `bg-surface` → `bg-surface-raised`), not drop shadow, per the dark-console mood. The one exception: modals get a single soft shadow (`0 8px 24px rgba(0,0,0,0.4)`) purely to separate them from the page behind an overlay scrim (`rgba(0,0,0,0.6)`).

---

## 4. Screen Inventory

| # | Screen | Purpose |
|---|---|---|
| 1 | **City / Network Setup** | Pick a pre-cached Indian city, upload delivery-node CSV, configure vehicle capacity, place an accident-injection marker |
| 2 | **Live Optimization Run** | Both solvers running concurrently; live SSE convergence chart; visible seed/time-budget for fairness transparency |
| 3 | **Results Comparison** | Dual map (classical vs. quantum route), route table with per-route totals, hover-to-inspect edge travel time |
| 4 | **Green Impact Dashboard** | CO2/fuel/time-saved deltas, sourced-assumption modal trigger |
| 5 | **"How It Works" modal** | QPSO formulas (ROV mapping, attractor equation, mbest, Monte Carlo update, α-schedule) — hidden by default, one click away, for technically literate judges only |

These five map directly and exhaustively to the PRD's user stories (Section 5) — no screen exists that isn't traceable to a specific PRD requirement, and no PRD-required capability lacks a screen.

---

## 5. User Flows

### Flow A — Fleet Manager: upload → configure → run → results
1. **Setup screen:** select city from dropdown (pre-cached list only, no free-text search — prevents the "uncached city" failure state from being reachable by an unconstrained input) → upload CSV (template link visible) → set vehicle capacity in a single numeric field → primary CTA **"Run Optimization"** becomes enabled only once city + valid CSV are both present.
2. Clicking **Run Optimization** navigates to the **Live Run** screen immediately (no intermediate confirmation screen — the PRD's <15s latency target means waiting is itself part of the demo, not dead time to hide behind a spinner-only transition).
3. Live Run screen streams the convergence chart; a persistent **"View Results"** button is disabled (greyed, with a tooltip "waiting for both solvers") until the `event: complete` SSE payload arrives for both algorithms, then it auto-highlights (pulses once) to invite the click.
4. **Results Comparison** screen opens by default; a secondary tab/link surfaces the **Green Impact Dashboard**.

### Flow B — Technical Evaluator: watch convergence → inspect math → inspect benchmark numbers
1. Judge is handed the app already on the **Live Run** screen (rehearsed primary scenario, per PRD Section 16) — convergence chart already animating.
2. A visibly-labeled, low-emphasis **"How It Works ⓘ"** button sits in the top-right of the Live Run screen at all times (not buried in a menu) — clicking opens the modal as an overlay *without* interrupting the SSE stream underneath (the chart keeps updating behind the scrim; closing the modal shows no data gap).
3. Modal shows the QPSO formula block (Section 6.2 layout below) plus a small "seed: `#12345` · time budget: `5.0s` · OR-Tools version: `x.y.z`" reproducibility footer — this is the fairness-transparency proof point from the PRD's seeding directive, made visible rather than left in a log file.
4. Closing the modal returns to Live Run, then Results Comparison once solving completes; the results table (Section 6.3) is the "side-by-side benchmark numbers" this flow ends on.

### Flow C — Traffic Analyst: inject accident → observe re-optimization
1. On **Setup screen**, after a scenario is loaded, an **"Inject Accident"** toggle switches the map cursor into edge-select mode; clicking a road segment marks it with a `status-error`-colored dashed overlay and a small "×5 delay" chip.
2. Clicking **Run Optimization** re-runs both solvers against the modified matrix — same Live Run and Results screens as Flow A, but the Results Comparison screen now shows a small **"Re-route triggered by accident on [edge]"** caption above the map so the judge understands *why* the routes differ from a prior run, not just that they do.

---

## 6. Per-Screen Layout

### 6.1 City / Network Setup
- **Hierarchy:** left panel (30% width) = controls (city dropdown, CSV upload dropzone, capacity input, accident toggle); right (70%) = live map preview of the selected city's cached graph, updating as soon as a city is picked.
- **Primary action:** "Run Optimization" button, sticky at the bottom of the left panel, full-width.
- **Components:** `Dropdown`, `FileDropzone`, `NumericInput`, `ToggleButton` (accident mode), `MapCanvas` (dual-route component, used here in single-layer preview mode), `StatusBadge` ("cached" / "not cached").

### 6.2 Live Optimization Run
- **Hierarchy:** full-width top bar showing the fairness footer (seed / time budget / versions, small, monospace); center = the convergence chart (dominant element, per P1); below/beside it two compact **`AlgorithmStatusCard`**s (one per algorithm, colored per their token) each showing a live-updating current-best figure and elapsed time.
- **Primary action:** none required from the user during the run — the screen is observational; the only interactive element is the "How It Works" info button (top-right) and a disabled-until-ready "View Results" CTA.
- **Components:** `ConvergenceChart` (streaming), `AlgorithmStatusCard` ×2, `FairnessFooter`, `HowItWorksTrigger`, `SSEConnectionIndicator`.

### 6.3 Results Comparison
- **Hierarchy:** top = dual-map view (side-by-side or toggle-overlay — see Section 9 for the breakpoint decision) with both route colors rendered simultaneously per P2; below = a single **`RouteComparisonTable`** with one row per algorithm (total distance, total time, total CO2, feasibility ✓/✗) so the delta is read top-to-bottom, not left-to-right across a wide screen.
- **Primary action:** "View Green Impact →" CTA, leading into screen 4.
- **Components:** `MapCanvas` (dual-layer mode), `EdgeHoverTooltip`, `RouteComparisonTable`, `RouteLegend` (color + pattern key, always visible, never assume the judge remembers the color mapping from a previous screen).

### 6.4 Green Impact Dashboard
- **Hierarchy:** three `StatCard`s across the top (CO2 saved, fuel saved, time saved), each with a large `text-stat-lg` delta number in `accent-eco` and a small "vs. unoptimized nearest-neighbor baseline" caption; below, a single "Assumptions ⓘ" link opens the sourcing modal.
- **Primary action:** none — this is a terminal/read screen in the flow; back-navigation only.
- **Components:** `StatCard` ×3, `AssumptionsModalTrigger`, `RiskMitigationCallout` (used here to state the IPCC-proxy caveat from PRD Section 13 inline, not just inside the modal — the caveat must be visible without a click, per P3).

### 6.5 "How It Works" modal
- **Hierarchy:** three stacked sections — (1) plain-language one-paragraph summary at the top for a non-technical judge who opens it by mistake, (2) the formula block (ROV, attractor, mbest, Monte Carlo update, α-schedule) rendered as static LaTeX-style math images or MathJax, monospace-labeled, (3) the reproducibility footer (seed/time-budget/versions) repeated here too, since a judge may open this modal without having seen the Live Run screen's footer.
- **Primary action:** "Close" only.
- **Components:** `Modal`, `MathFormulaBlock`, `FairnessFooter` (reused from 6.2).

---

## 7. Component Library

| Component | Variants | States |
|---|---|---|
| **`MapCanvas`** (dual-route layer) | `single-layer` (Setup screen preview), `dual-layer-side-by-side`, `dual-layer-overlay-toggle` (Results screen, breakpoint-dependent per Section 9) | loading (skeleton graph), loaded, hover (edge tooltip active), error (city not cached), accident-edit-mode |
| **`ConvergenceChart`** (streaming) | two-line (classical + quantum overlay) | live-streaming (appends points without full re-render — see implementation note below), frozen/disconnected (dimmed + reconnect badge), complete (final state, lines locked, "winner" marker on lower final value), error (chart area replaced by error message, not left blank) |
| **`RouteComparisonTable`** | 2-row (MVP: one per algorithm) | loading (skeleton rows), populated, — no error state needed at this component level (errors surface at the screen level via the error banner, not inline in a table) |
| **`StatCard`** | `eco` (green accent, used only on Green Impact screen), `neutral` (used for generic figures elsewhere if ever needed) | loading (shimmer), populated, — |
| **`RiskMitigationCallout`** | `warning` (amber, e.g. "assumption" caveats), `error` (red, e.g. "solver crashed" explanations) | static (no interactive states — this is a read-only inline notice) |
| **`AlgorithmStatusCard`** | `classical`, `quantum` (color-locked per token) | running (pulse dot, `status-live`), complete, error |
| **`SSEConnectionIndicator`** | — | connected (small green dot, unobtrusive), reconnecting (amber pulsing dot + "reconnecting…" text), failed (red dot + manual retry button) |
| **`FairnessFooter`** | — | static text, no states |

**`ConvergenceChart` streaming implementation note:** use a chart library that supports **imperative point-append** (e.g., a lightweight canvas-based chart, or Recharts driven by a state array where only the array grows and the component avoids full-dataset re-diffing on each SSE tick — batch incoming SSE points on a `requestAnimationFrame` tick, e.g. every 100–150ms, rather than re-rendering per individual SSE message) — this is a deliberate performance choice: at high iteration counts, re-rendering the full chart per single data point will visibly stutter, which undercuts P1's "instantly legible" requirement by making the hero visual look broken.

---

## 8. States

| Screen | Empty | Loading | Error | Success | Offline/disconnected |
|---|---|---|---|---|---|
| Setup | N/A — a default scenario is always pre-loaded (PRD Section 16, "no screen ever empty") | Map graph loading skeleton (grey wireframe of the target city's rough shape, not a generic spinner, to signal "real map incoming") | "City not cached" — see below | City map rendered, CSV validated (green checkmark chip) | N/A (no live network dependency on this screen) |
| Live Run | N/A | Chart axis drawn, both `AlgorithmStatusCard`s show "initializing…" | Solver-crashed state — see below | Both cards show "complete", chart locked | SSE-disconnected state — see below |
| Results | N/A (only reachable after success) | Skeleton map + skeleton table rows | Generic error banner ("results unavailable — [retry]") if results fetch fails independently of the solver run itself | Dual routes rendered, table populated | N/A |
| Green Impact | N/A | Skeleton stat cards | Same generic error banner pattern | Stat cards populated with sourced caveat visible | N/A |

**SSE-disconnected state (explicit design, per PRD Section 15):** `SSEConnectionIndicator` flips to "reconnecting…" (amber pulse); the `ConvergenceChart` freezes its last-known line (does not clear, does not reset to zero) and gets a subtle diagonal-hatch overlay tint to communicate "stale, not live" without hiding the data; on reconnect, the chart un-hatches and the line continues from the replayed full history (per the backend's cache-replay behavior) — visually this should look like a brief pause, never a re-drawn-from-scratch chart, since a full redraw would misleadingly suggest data was lost.

**Solver-crashed state (explicit design):** the `ConvergenceChart` area is replaced entirely by a `RiskMitigationCallout` in its `error` variant: a clear one-line message ("QPSO solver failed: [reason]"), a monospace error detail line (collapsed by default, expandable), and a single **"Retry"** button that re-submits the same job (same seed, same scenario) — never an infinite spinner, matching the PRD's explicit failure-mode requirement.

**"City not cached" state (explicit design):** the city dropdown only lists cities that *are* cached (Section 5/6.1's design already prevents this from being reachable via normal use) — but as defense-in-depth if a judge somehow triggers an uncached-city request (e.g., a stale bookmark), the Setup screen's map panel shows a `status-warning`-colored notice: "This city isn't pre-cached for offline use. Pick one from the list to continue." with the dropdown auto-focused — no attempt to fetch live from Overpass is ever made from the running app, consistent with the PRD's zero-live-network-dependency mandate.

---

## 9. Responsive Behaviour

**Primary target: laptop screen, ≥1280px wide, landscape.** This is a live-demo tool, not a public product — graceful mobile degradation is explicitly **not** a priority, and this brief flags rather than silently handles the tradeoff:

- **Results Comparison's dual-map view assumes ≥1280px** to show both routes side-by-side with legible labels. Below that breakpoint (flagged explicitly), the layout must collapse to a **single map with an overlay toggle** (switch between "show classical" / "show quantum" / "show both overlaid") rather than attempt a cramped side-by-side — this is a real design decision the brief is making now, not deferring, because the Results screen is the one place a bad breakpoint choice would visibly break the P1 hero comparison.
- **Live Run's convergence chart + two status cards** reflow to a stacked (chart on top, cards below, full-width) layout below ~1024px — lower risk, since a chart's legibility degrades gracefully with width in a way a dual-map's doesn't.
- **Tablet/mobile are explicitly out of scope for functional QA** in the 36-hour window — the CSS should not *break* (no horizontal scroll, no overlapping text) at tablet width as a baseline safety net, but no dedicated tablet layout work is planned or needed, since the judged demo runs on the team's own laptop.

---

## 10. Accessibility — right-sized for a hackathon demo tool

**Load-bearing (must be correct, because the judging criteria and the colorblind-safety requirement depend on it):**
- **Contrast:** all `text-primary`/`text-secondary` on `bg-canvas`/`bg-surface` must meet **WCAG AA (4.5:1)** minimum for body text, **3:1** for large stat numerals — verify the specific hex pairs in Section 3.1 against this before build, not after.
- **Colorblind-safe route colors:** the blue/orange pairing plus the solid/dashed line-pattern redundancy (Section 3.1) is load-bearing — this is an explicit PRD-adjacent requirement (the prompt itself calls it out), not a nice-to-have, because a judge with color-vision deficiency must be able to read the core comparison unaided.
- **Legend always visible:** the `RouteLegend` on the Results screen (Section 6.3) must never be hidden behind a hover or a collapsed accordion — a judge should not need to discover it.

**Lighter-touch (acceptable to under-build given the 36-hour window, stated explicitly so it's a decision, not an oversight):**
- **Full keyboard navigation** across every interactive element: nice to have for the CSV upload and dropdown controls (likely free via standard HTML form elements), but **not** worth custom engineering effort for the map's edge-click accident-injection interaction — that interaction can remain mouse-only for the demo.
- **Full ARIA labeling** of the live-updating chart and SSE status indicators: skip building a screen-reader-optimized live-region announcement pipeline for the streaming chart — this is a genuinely hard problem (announcing every SSE tick would be unusable for a screen-reader user regardless) and is not what any judge will evaluate in a 90-second glance. A basic `aria-label` on static controls (buttons, dropdowns) is sufficient; a fully accessible live-data experience is explicitly deferred past the hackathon.
