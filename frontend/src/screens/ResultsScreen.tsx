import { useEffect, useState } from 'react';
import { fetchEdges } from '../api/client';
import type { GraphEdge } from '../api/types';
import { useAppActions, useAppState } from '../state/AppState';
import { MapCanvas } from '../components/LazyMapCanvas';
import { RouteComparisonTable } from '../components/RouteComparisonTable';
import { RouteLegend } from '../components/RouteLegend';

export function ResultsScreen() {
  const { result, scenario } = useAppState();
  const { goTo } = useAppActions();
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  // Real road network as map context, same as the Setup screen -- routes
  // are drawn over real streets, not a blank canvas.
  useEffect(() => {
    if (!scenario?.cityId) return;
    fetchEdges(scenario.cityId).then(setEdges).catch(() => setEdges([]));
  }, [scenario?.cityId]);

  if (!scenario) return null;

  if (!result || result.status !== 'done') {
    return (
      <div style={{ padding: 'var(--space-6)' }}>
        <h1 className="text-display">Results Comparison</h1>
        <p className="text-body">
          {result?.status === 'error' ? `Solver error: ${result.detail}` : 'Waiting for both solvers to finish…'}
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="text-display">Results Comparison</h1>
        <RouteLegend />
      </div>

      {result.accident_edge && (
        <p className="text-caption" style={{ color: 'var(--status-warning)' }}>
          Re-route triggered by an injected accident (×5 delay on the selected road segment)
        </p>
      )}

      <MapCanvas
        nodes={scenario.nodes}
        heightPx={480}
        edges={edges}
        selectedEdgeId={
          result.accident_edge
            ? `${Math.min(result.accident_edge.from_node_id, result.accident_edge.to_node_id)}_${Math.max(result.accident_edge.from_node_id, result.accident_edge.to_node_id)}`
            : null
        }
        routeLayers={[
          { routes: result.ortools.routes, color: [46, 107, 230], dashed: false },
          { routes: result.qpso.routes, color: [232, 135, 30], dashed: true },
        ]}
      />

      <RouteComparisonTable ortools={result.ortools} qpso={result.qpso} />

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
