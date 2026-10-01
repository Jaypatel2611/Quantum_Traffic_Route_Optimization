import type { ScenarioNode } from '../api/types';

/** Every node loaded from the CSV -- the same list the map plots, so nothing
 * uploaded is invisible. Row 0 is the depot. */
export function NodeTable({ nodes }: { nodes: ScenarioNode[] }) {
  if (nodes.length === 0) return null;
  return (
    <details>
      <summary className="text-caption" style={{ cursor: 'pointer' }}>
        Nodes ({nodes.length}) — total demand {nodes.reduce((sum, n) => sum + n.demand, 0)}
      </summary>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 'var(--space-2)' }}>
        <thead>
          <tr className="text-caption">
            <th style={{ textAlign: 'left' }}>Node</th>
            <th style={{ textAlign: 'right' }}>Demand</th>
            <th style={{ textAlign: 'right' }}>Lat, Lon</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((n, i) => (
            <tr key={n.id}>
              <td className="text-caption">{i === 0 ? `${n.id} (depot)` : n.id}</td>
              <td className="text-caption" style={{ textAlign: 'right' }}>{n.demand}</td>
              <td className="text-caption" style={{ textAlign: 'right' }}>{n.lat.toFixed(4)}, {n.lon.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
