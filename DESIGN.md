---
name: Quantum Traffic Route Optimization
description: A dark operational console for a head-to-head classical-vs-quantum-inspired route optimizer — the comparison is the hero.
colors:
  route-classical: "#2e6be6"
  route-quantum: "#e8871e"
  bg-canvas: "#12161c"
  bg-surface: "#1b212b"
  bg-surface-raised: "#232b38"
  border-subtle: "#2e3742"
  text-primary: "#edeff2"
  text-secondary: "#9aa5b1"
  accent-eco: "#2fbf71"
  status-error: "#e5484d"
  status-warning: "#f2c94c"
  status-live: "#2fbf71"
typography:
  display:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "40px"
  h2:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: "28px"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
  caption:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "16px"
  stat-lg:
    fontFamily: "IBM Plex Mono, ui-monospace, Consolas, monospace"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: "32px"
  stat-sm:
    fontFamily: "IBM Plex Mono, ui-monospace, Consolas, monospace"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "20px"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
  "12": "48px"
  "16": "64px"
components:
  button-primary:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.bg-canvas}"
    rounded: "{rounded.md}"
    padding: "12px 24px"
  button-primary-disabled:
    backgroundColor: "{colors.bg-surface-raised}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "12px 24px"
  button-ghost:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  stat-card:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "16px"
  modal-surface:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "24px"
---

# Design System: Quantum Traffic Route Optimization

## Overview

**Creative North Star: "The Operations Console"**

This is an engineering console, not a consumer app — the references that actually landed in the build are QGIS/Mapbox Studio-style map-first layout, Grafana/Datadog-style dense monospace stat tiles, and Palantir Foundry's flat dark operational chrome. Every screen exists to show one comparison — OR-Tools (classical) against QPSO (quantum-inspired) — never one algorithm's output alone. The palette is functional, not decorative: two colors carry algorithm identity, one color carries eco-positive figures, and everything else is neutral lightness-stepped gray. There is exactly one theme; light mode was never built and is out of scope.

Confirmed rejections, carried from the brief and honored by the shipped code: no purple/violet gradients, no glowing particle/neural-net/"quantum swirl" motifs, no rounded bubbly consumer-SaaS cards, no illustrated/cartoon empty states, no decorative rainbow color use, no Unicode/emoji glyphs standing in for icons.

**Key Characteristics:**
- Flat dark chrome, depth by lightness step (canvas → surface → surface-raised), never by shadow, except modals.
- Inter for UI text, IBM Plex Mono for every measured number — the mono face is the "this is a real read-out" signal.
- A colored left border is the app's one color-encoding mechanism, reused identically on every stat/status tile.
- Two colors are reserved: they mean one thing each, everywhere, and nothing else.

## Colors

The palette is small and role-locked: two identity colors, one eco color, one warm neutral scale, and three status colors. Nothing is decorative.

### Primary
- **Classical Blue** (`#2e6be6`, `{colors.route-classical}`): OR-Tools' one and only color. Solid line on the map, solid legend swatch, left border on its AlgorithmStatusCard/StatCard. Never appears on a screen that isn't reporting on OR-Tools specifically.
- **Quantum Amber** (`#e8871e`, `{colors.route-quantum}`): QPSO's one and only color, always paired with a dashed line/border as the redundant (colorblind-independent) encoding channel. Same rule as Classical Blue: algorithm identity only.

### Secondary
- **Eco Green** (`#2fbf71`, `{colors.accent-eco}`): reserved for CO2/fuel/time-saved positive figures on the Green Impact screen only (also doubles as `--status-live` for a genuinely live/streaming indicator, a distinct meaning from "eco," not a repurposing of it into generic UI accent).

### Node Identity
- **Node Identity Palette** (10 hand-picked hues × 2 lightness steps, `frontend/src/utils/nodeColor.ts`): every non-depot delivery node gets a deterministic color hashed from its id — the same node is the same color on the Setup map and the Results map, so a judge or fleet manager can visually track one specific delivery point across screens. This is identity encoding, not decoration: it answers "which node is this," a different question from the route colors' "which algorithm." The 10 hues are hand-picked to stay clear of `--route-classical` (blue, ~221°), `--route-quantum` (amber, ~30°), `--accent-eco` (green, ~152°), and the brief's rejected purple/violet band (~260–300°) — never draw a node-identity color from those ranges. The depot node stays `--text-primary` white, unchanged, since it isn't a "which node" question. This is a scoped exception to Brand Commitments' "avoid decorative rainbow color use": the exception applies only to per-node identity dots, and only because each color is a stable, meaningful pointer back to one node, never assigned arbitrarily or reused as chrome.

### Neutral
- **Canvas** (`#12161c`, `{colors.bg-canvas}`): page background, the darkest step.
- **Surface** (`#1b212b`, `{colors.bg-surface}`): the default card/tile/panel background, one lightness step up from canvas.
- **Surface Raised** (`#232b38`, `{colors.bg-surface-raised}`): disabled-button fill and any surface that needs to read as "above" a Surface tile without a shadow.
- **Border Subtle** (`#2e3742`, `{colors.border-subtle}`): the only border color; used for panel dividers, sticky-footer rules, and input strokes.
- **Text Primary** (`#edeff2`, `{colors.text-primary}`): headings, primary body text, and — inverted — the fill of the enabled primary CTA.
- **Text Secondary** (`#9aa5b1`, `{colors.text-secondary}`): captions, disabled-state text, secondary labels.
- **Status Error** (`#e5484d`, `{colors.status-error}`): error text and the solver-error banner fill only.
- **Status Warning** (`#f2c94c`, `{colors.status-warning}`): reserved for caveat/assumption callouts (e.g. the COPERT-model-is-a-proxy notice) — a warning about a number's provenance, not a generic accent.

### Named Rules
**The One Meaning Rule.** `--route-classical`, `--route-quantum`, and `--accent-eco` each mean exactly one thing — algorithm identity for the first two, eco-positive-figure for the third — and are never reused as a generic UI accent, decorative highlight, or brand color anywhere else in the app. This was the system's one material defect caught in finish review (these tokens had leaked onto generic chrome) and the fix is now the rule: before adding either route color or the eco color to any new element, confirm the element is reporting OR-Tools/QPSO output or an eco figure specifically — if not, use a neutral.

**The Border-Encodes Rule.** Color-coding a tile to an algorithm or context is done with a 3px solid left border on an otherwise neutral (`bg-surface`) card, never by tinting the card's background or text. This keeps every number legible against the same dark neutral regardless of which color it's attached to.

## Typography

**Display/Body Font:** Inter (with `system-ui, sans-serif` fallback)
**Label/Mono Font:** IBM Plex Mono (with `ui-monospace, Consolas, monospace` fallback)

**Character:** A plain grotesque for structure and prose, handed off to a monospace face the instant a value is a measured number — the pairing is what makes a stat tile read as instrument output rather than copy.

### Hierarchy
- **Display** (600, 32px/40px): screen-level `<h1>` titles only ("City / Network Setup", "Live Optimization Run").
- **Title/H2** (600, 20px/28px): sub-section headings inside a screen (e.g. "Convergence", modal titles).
- **Body** (400, 14px/20px): all prose, labels, form fields, button text.
- **Caption** (400, 12px/16px, `--text-secondary`): captions, legend labels, fairness-footer metadata, assumption notes.
- **Stat Large** (mono, 600, 28px/32px): the headline number on a StatCard/AlgorithmStatusCard — the single figure a judge scans for.
- **Stat Small** (mono, 400, 16px/20px): inline numeric values that aren't a card's headline figure.

### Named Rules
**The Measured-Number Rule.** Any value that is read off a solver, a sensor, or a computation (fitness scores, seeds, time budgets, CO2/fuel/time deltas, elapsed time) renders in `--font-mono`. Inter is reserved for everything that is prose or a label, never a measurement.

## Layout

Density over illustration: every screen is a working panel, never an empty/marketing layout. Two structural patterns cover all five screens:
- **Split-panel** (Setup screen): a fixed 30%/70% split — a scrollable control column (min-width 320px) on the left with a sticky, full-width primary CTA pinned to its own bottom edge, and a live map preview filling the remaining 70%.
- **Stacked-panel** (Live Run, Results, Green Impact): a single `padding: var(--space-6)` column, `flex-direction: column`, `gap: var(--space-4)` to `var(--space-6)` between major blocks (title row → chart/map → stat/status row → comparison detail → primary CTA).

Spacing is strictly 4px-based (`--space-1` 4px through `--space-16` 64px); screen padding is always `--space-6` (24px), inter-block gaps are `--space-4`–`--space-6`, and tight internal gaps (label-to-input, icon-to-label) are `--space-2`.

**The Real-Roads-Always-On Rule.** Every MapCanvas instance (Setup, Results) fetches and draws the city's real road-edge network as a neutral background layer (`--border-subtle`, 1.5px, no click handler outside accident-pick mode) as soon as a city is known — routes and nodes are never plotted against a blank canvas. Previously the road network only appeared while picking an accident edge; both maps now always show it, since a blank canvas with floating dots reads as unfinished, and route lines only make sense laid over the streets they actually follow.

### Named Rules
**The Sticky-CTA Rule.** A screen's one primary action button (Run Optimization, View Results, View Green Impact) sits in a `position: sticky; bottom: 0` footer with a `--border-subtle` top rule and `--bg-canvas` background, so it stays reachable without scroll regardless of column content length — the fix for a finish-review finding that a CTA could go off-viewport on a long panel; keep any new primary CTA sticky, don't rely on natural document flow.

## Elevation & Depth

Flat by default: the console conveys depth entirely through a three-step lightness ramp (`bg-canvas` → `bg-surface` → `bg-surface-raised`), never through `box-shadow`, on every persistent surface. The single exception is the Modal, whose backdrop-overlay pattern (a `rgba(0,0,0,0.6)` scrim plus a raised surface) is a genuine state change — content interrupting the console — and is the only place a shadow (`0 8px 24px rgba(0,0,0,0.4)`) appears. A one-shot `pulse-once` box-shadow ring animation fires exactly once when the "View Results" CTA becomes enabled, as an affordance cue, not ambient elevation.

### Shadow Vocabulary
- **Modal elevation** (`box-shadow: 0 8px 24px rgba(0,0,0,0.4)`): the modal panel only, over its scrim.
- **Enable-pulse** (`pulse-once` keyframe, `box-shadow: 0 0 0 0/10px rgba(237,239,242,0.5→0)`): fires once when a gated primary CTA becomes clickable.

### Named Rules
**The Flat-Except-Interrupt Rule.** Shadows exist only where content interrupts the console (the modal). Any persistent screen surface — card, panel, footer, sticky bar — stays flat and differentiates itself from its background purely by lightness step.

## Shapes

Small, consistent radii throughout: `--radius-sm` (4px) for inputs, selects, and secondary/ghost buttons; `--radius-md` (6px) for stat cards, status cards, primary buttons, and the disabled-button state; `--radius-lg` (8px) for the modal surface only, the one larger/softer shape reserved for the one overlay component. Borders are always 1px `--border-subtle`, used for panel dividers and input/select strokes — never a color border for emphasis (emphasis is the 3px colored left-border convention instead).

## Components

### Buttons
- **Shape:** `--radius-sm` (ghost/secondary), `--radius-md` (primary).
- **Primary:** enabled state fills `--text-primary` with `--bg-canvas` text (an inverted-neutral fill, not a color accent); disabled state fills `--bg-surface-raised` with `--text-secondary` text. Padding `var(--space-3) var(--space-6)` (full-width sticky variant) or `var(--space-4)`.
- **Ghost:** `--bg-surface` fill, `--text-secondary` text, 1px `--border-subtle` border, `var(--space-2) var(--space-3)` padding — used for secondary actions ("How It Works", disabled "Inject Accident").
- **Focus:** a uniform `2px solid var(--text-primary)` focus-visible outline with `2px` offset on every interactive element (button/input/select/link) — one focus treatment, not per-component.

### Cards / Containers (StatCard, AlgorithmStatusCard)
- **Corner Style:** `--radius-md` (6px).
- **Background:** `--bg-surface`, flat, never tinted by the value it reports.
- **Color assignment:** a 3px solid left border in the relevant identity color (`--route-classical`/`--route-quantum`) or `--accent-eco` — the app's single color-encoding mechanism, applied identically whether the card is reporting algorithm progress (AlgorithmStatusCard) or a result figure (StatCard).
- **Internal Padding:** `var(--space-4)` (16px).
- **Contents:** a `text-caption` label, a `text-stat-lg` mono headline value, an optional `text-caption` supporting caption below.

### Modal
- **Corner Style:** `--radius-lg` (8px), the system's one larger radius.
- **Background:** `--bg-surface` panel over a `rgba(0,0,0,0.6)` full-screen scrim; the only component with a shadow.
- **Behavior:** click on scrim closes, click inside panel does not propagate; `role="dialog"` `aria-modal="true"`; a drawn `×` close glyph (SVG cross via text glyph — not an emoji icon) top-right.
- **Padding:** `var(--space-6)` (24px), max-width 640px / 90% width, max-height 85vh with internal scroll.

### Signature Component: InfoIcon (drawn-icon convention)
Every icon in the app is a hand-drawn inline SVG at a single consistent stroke weight (1.3px) and size (14–16px), `currentColor`-based so it inherits its context's text color — never a Unicode/emoji character standing in for an icon. InfoIcon (a circled lowercase "i") is the canonical instance, used next to every "Assumptions"/"How It Works" disclosure trigger. Any future icon must be built the same way: one SVG, one stroke weight, `currentColor`, `aria-hidden="true"`.

### Legend (RouteLegend)
A small inline `text-caption` row pairing each identity color with its dashed/solid line-sample and a text label ("OR-Tools (classical)", "QPSO (quantum-inspired)") — repeated on every screen where both route colors appear on a map or chart, so the mapping is never assumed to be remembered from a previous screen.

## Do's and Don'ts

### Do:
- **Do** render every measured number (fitness value, seed, time budget, CO2/fuel/time delta) in `--font-mono` (`text-stat-lg`/`text-stat-sm`/mono caption), never in Inter.
- **Do** encode algorithm or eco-figure identity with a 3px solid colored left border on an otherwise neutral `--bg-surface` card — never by tinting card background or text color.
- **Do** pair `--route-quantum` with a dashed stroke and `--route-classical` with a solid stroke everywhere a route/line appears, as the colorblind-safe redundant channel.
- **Do** pad a small/near-flat data series' Y-axis domain (see ConvergenceChart's `paddedDomain`) so a real-but-flat convergence line stays visibly drawn above the axis rather than reading as an empty chart.
- **Do** keep a screen's one primary CTA in a `position: sticky; bottom: 0` footer.
- **Do** draw every icon as an inline SVG at one consistent stroke weight — never a Unicode/emoji glyph.

### Don't:
- **Don't** reuse `--route-classical`, `--route-quantum`, or `--accent-eco` as a generic UI accent, hover color, or decorative highlight on chrome that isn't reporting that specific algorithm's or eco figure's data — this is the system's one hard-won rule; it was violated once, caught in finish review, and fixed.
- **Don't** add a `box-shadow` to a persistent screen surface (card, panel, sticky bar); shadows are reserved for the modal's overlay interrupt only.
- **Don't** introduce a second font family, an emoji/Unicode icon, a purple/violet gradient, or a "quantum swirl" particle motif — all explicitly rejected by the brief and absent from the shipped build.
- **Don't** show one algorithm's result alone on a primary screen; the comparison (both colors, both figures, side by side) is the unit of display.
