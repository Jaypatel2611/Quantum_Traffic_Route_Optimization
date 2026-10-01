import { useEffect, useMemo, useState } from 'react';
import { fetchEdges } from '../api/client';
import type { AlgorithmResult, GraphEdge } from '../api/types';
import { useAppActions, useAppState } from '../state/AppState';
import { MapCanvas } from '../components/LazyMapCanvas';
import { RouteComparisonTable } from '../components/RouteComparisonTable';
import { RouteLegend } from '../components/RouteLegend';
import { MapLegend } from '../components/MapLegend';
import { RouteBreakdown } from '../components/RouteBreakdown';
import { BackButton } from '../components/BackButton';
import { VehicleSelector } from '../components/VehicleSelector';
import { routeKey, vehicleColor, type Solver } from '../utils/vehicleColor';
import { edgeIdFor } from './SetupScreen';

/** "OR-Tools: v0 stop 2 · QPSO: v1 stop 1" per node, for the map tooltip --
 * read straight off the solvers' returned sequences. */
function visitNotes(ortools: AlgorithmResult, qpso: AlgorithmResult): Record<string, string> {
  const notes: Record<string, string[]> = {};
  for (const [label, result] of [['OR-Tools', ortools], ['QPSO', qpso]] as const) {
    for (const route of result.routes) {
      route.node_sequence.slice(1, -1).forEach((id, i) => {
        (notes[id] ??= []).push(`${label}: ${route.vehicle_id} stop ${i + 1}`);
      });
    }
  }
  return Object.fromEntries(Object.entries(notes).map(([id, parts]) => [id, parts.join(' · ')]));
}

export function ResultsScreen() {
  const { result, scenario, visibleRoutes } = useAppState();
  const { goTo, setVisibleRoutes } = useAppActions();
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  // Real road network as map context, same as the Setup screen -- routes
  // are drawn over real streets, not a blank canvas.
  useEffect(() => {
    if (!scenario?.cityId) return;
    fetchEdges(scenario.cityId).then(setEdges).catch(() => setEdges([]));
  }, [scenario?.cityId]);

  const done = result && result.status === 'done' ? result : null;
  const nodeNotes = useMemo(() => (done ? visitNotes(done.ortools, done.qpso) : {}), [done]);
  const accidentIds = useMemo(
    () => (done ? done.accident_edges.map((a) => edgeIdFor(a.from_node_id, a.to_node_id)) : []),
    [done],
  );
  // Vehicle filter: every route keeps its color index from the full list, so
  // hiding v0 never recolors v1.
  const shown = useMemo(() => {
    const pick = (solver: Solver, algo: AlgorithmResult) => {
      const entries = algo.routes.map((route, i) => ({ route, color: vehicleColor(solver, i) }));
      return entries.filter(({ route }) => visibleRoutes === null || visibleRoutes.includes(routeKey(solver, route.vehicle_id)));
    };
    return done ? { ortools: pick('ortools', done.ortools), qpso: pick('qpso', done.qpso) } : null;
  }, [done, visibleRoutes]);
  const reroutedPaths = useMemo(
    () => (shown ? [...shown.ortools, ...shown.qpso].flatMap(({ route }) => route.rerouted_geometry ?? []) : []),
    [shown],
  );

  if (!scenario) return null;

  if (!done) {
    return (
      <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <BackButton label="Back to Setup" disabled={result?.status !== 'error'} />
        <h1 className="text-display">Results Comparison</h1>
        <p className="text-body">
          {result?.status === 'error' ? `Solver error: ${result.detail}` : 'Waiting for both solvers to finish…'}
        </p>
      </div>
    );
  }

  if (!shown) return null;

  return (
    <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <BackButton label="Back to Setup" />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="text-display">Results Comparison</h1>
        <RouteLegend />
      </div>

      {done.accident_edges.length > 0 && (
        <p className="text-caption" style={{ color: 'var(--status-warning)' }} data-testid="accident-banner">
          Re-routed around {done.accident_edges.length} injected accident{done.accident_edges.length > 1 ? 's' : ''} (×5
          delay on each selected road segment: {accidentIds.join(', ')}). Edit them via Back to Setup.
        </p>
      )}

      <MapLegend showAccidents={accidentIds.length > 0} showRerouted={accidentIds.length > 0} />
      <VehicleSelector ortools={done.ortools} qpso={done.qpso} visible={visibleRoutes} onChange={setVisibleRoutes} />
      <MapCanvas
        nodes={scenario.nodes}
        heightPx={480}
        edges={edges}
        selectedEdgeIds={accidentIds}
        reroutedPaths={reroutedPaths}
        nodeNotes={nodeNotes}
        routeLayers={[
          { routes: shown.ortools.map((e) => e.route), colors: shown.ortools.map((e) => e.color), color: [46, 107, 230], dashed: false },
          { routes: shown.qpso.map((e) => e.route), colors: shown.qpso.map((e) => e.color), color: [232, 135, 30], dashed: true },
        ]}
      />

      <RouteComparisonTable ortools={done.ortools} qpso={done.qpso} />

      <RouteBreakdown
        label="OR-Tools (classical) — route"
        color="var(--route-classical)"
        result={{ ...done.ortools, routes: shown.ortools.map((e) => e.route) }}
        nodes={scenario.nodes}
        vehicleCapacity={scenario.vehicleCapacity}
      />
      <RouteBreakdown
        label="QPSO (quantum-inspired) — route"
        color="var(--route-quantum)"
        result={{ ...done.qpso, routes: shown.qpso.map((e) => e.route) }}
        nodes={scenario.nodes}
        vehicleCapacity={scenario.vehicleCapacity}
      />

      <div
        style={{
          position: 'sticky', bottom: 0, background: 'var(--bg-canvas)',
          borderTop: '1px solid var(--border-subtle)', padding: 'var(--space-4) 0', marginTop: 'var(--space-2)',
        }}
      >
        <button
          onClick={() => goTo('green-impact')}
          style={{
            padding: 'var(--space-3) var(--space-6)',
            background: 'var(--text-primary)', color: 'var(--bg-canvas)',
            border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 600,
          }}
        >
          View Green Impact →
        </button>
      </div>
    </div>
  );
}
