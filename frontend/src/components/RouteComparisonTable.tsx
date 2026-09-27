import type { CSSProperties } from 'react';
import type { AlgorithmResult } from '../api/types';

interface RouteComparisonTableProps {
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
}

/** One row per algorithm (not one column per algorithm) so the delta reads
 * top-to-bottom -- Design Brief 6.3's explicit layout call. */
export function RouteComparisonTable({ ortools, qpso }: RouteComparisonTableProps) {
  const totalDistance = (r: AlgorithmResult) => r.routes.reduce((sum, route) => sum + route.total_distance_m, 0);

  const rows = [
    { label: 'OR-Tools (classical)', color: 'var(--route-classical)', result: ortools },
    { label: 'QPSO (quantum-inspired)', color: 'var(--route-quantum)', result: qpso },
  ];

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr className="text-caption">
          <th style={cellStyle('left')}>Algorithm</th>
          <th style={cellStyle('right')}>Distance (km)</th>
          <th style={cellStyle('right')}>Time (min)</th>
          <th style={cellStyle('right')}>CO2 (kg)</th>
          <th style={cellStyle('right')}>Feasible</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label} style={{ borderLeft: `3px solid ${row.color}` }}>
            <td className="text-body" style={cellStyle('left')}>{row.label}</td>
            <td className="text-stat-sm" style={cellStyle('right')}>{(totalDistance(row.result) / 1000).toFixed(2)}</td>
            <td className="text-stat-sm" style={cellStyle('right')}>{(row.result.total_time_s / 60).toFixed(1)}</td>
            <td className="text-stat-sm" style={cellStyle('right')}>{row.result.total_co2_kg.toFixed(2)}</td>
            <td className="text-stat-sm" style={cellStyle('right')}>{row.result.routes.length > 0 ? '✓' : '✗'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function cellStyle(align: 'left' | 'right'): CSSProperties {
  return { textAlign: align, padding: 'var(--space-2) var(--space-4)', borderBottom: '1px solid var(--border-subtle)' };
}
