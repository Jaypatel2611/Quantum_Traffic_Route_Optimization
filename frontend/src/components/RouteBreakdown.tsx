import type { CSSProperties } from 'react';
import type { AlgorithmResult, Route, ScenarioNode, Stop } from '../api/types';

interface RouteBreakdownProps {
  label: string;
  color: string;
  result: AlgorithmResult;
  nodes: ScenarioNode[];
  vehicleCapacity: number;
}

/** The optimizer's actual route per vehicle (stop order exactly as returned
 * by the solver -- nothing here re-sorts by demand or distance), with each
 * stop's demand from the CSV and the leg / cumulative distance and time the
 * solver's own matrices assign it. */
export function RouteBreakdown({ label, color, result, nodes, vehicleCapacity }: RouteBreakdownProps) {
  const demandOf = new Map(nodes.map((n) => [n.id, n.demand]));
  const depotId = nodes[0]?.id;
  const name = (id: string) => (id === depotId ? 'Depot' : id);

  return (
    <section
      style={{
        borderLeft: `3px solid ${color}`, paddingLeft: 'var(--space-4)',
        display: 'flex', flexDirection: 'column', gap: 'var(--space-3)',
      }}
    >
      <h2 className="text-body" style={{ fontWeight: 600 }}>{label}</h2>
      {result.routes.map((route) => (
        <RouteTable key={route.vehicle_id} route={route} demandOf={demandOf} name={name} vehicleCapacity={vehicleCapacity} />
      ))}
    </section>
  );
}

function RouteTable({
  route, demandOf, name, vehicleCapacity,
}: { route: Route; demandOf: Map<string, number>; name: (id: string) => string; vehicleCapacity: number }) {
  const rows = route.node_sequence.reduce<{ id: string; i: number; stop?: Stop; load: number }[]>(
    (acc, id, i) => {
      const previousLoad = acc[i - 1]?.load ?? 0;
      acc.push({ id, i, stop: route.stops?.[i], load: previousLoad + (i === 0 ? 0 : demandOf.get(id) ?? 0) });
      return acc;
    },
    [],
  );
  const totalLoad = rows[rows.length - 1]?.load ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <div className="text-caption" data-testid={`route-chain-${route.vehicle_id}`}>
        <strong>{route.vehicle_id}</strong>: {route.node_sequence.map(name).join(' → ')}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr className="text-caption">
            <th style={cell('left')}>#</th>
            <th style={cell('left')}>Node</th>
            <th style={cell('right')}>Demand</th>
            <th style={cell('right')}>Leg km</th>
            <th style={cell('right')}>Leg min</th>
            <th style={cell('right')}>Cum. km</th>
            <th style={cell('right')}>Cum. min</th>
            <th style={cell('right')}>Load</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ id, i, stop, load: runningLoad }) => (
            <tr key={`${id}-${i}`}>
              <td className="text-stat-sm" style={cell('left')}>{i === 0 ? 'start' : i === rows.length - 1 ? 'end' : i}</td>
              <td className="text-body" style={cell('left')}>{name(id)}</td>
              <td className="text-stat-sm" style={cell('right')}>{demandOf.get(id) ?? '—'}</td>
              <td className="text-stat-sm" style={cell('right')}>{stop ? (stop.leg_distance_m / 1000).toFixed(2) : '—'}</td>
              <td className="text-stat-sm" style={cell('right')}>{stop ? (stop.leg_time_s / 60).toFixed(1) : '—'}</td>
              <td className="text-stat-sm" style={cell('right')}>{stop ? (stop.cumulative_distance_m / 1000).toFixed(2) : '—'}</td>
              <td className="text-stat-sm" style={cell('right')}>{stop ? (stop.cumulative_time_s / 60).toFixed(1) : '—'}</td>
              <td className="text-stat-sm" style={cell('right')}>{runningLoad}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="text-caption" style={{ fontWeight: 600 }}>
            <td style={cell('left')} colSpan={3}>Route total</td>
            <td style={cell('right')} colSpan={2}>{(route.total_distance_m / 1000).toFixed(2)} km</td>
            <td style={cell('right')} colSpan={2}>{(route.total_time_s / 60).toFixed(1)} min</td>
            <td style={cell('right')}>{totalLoad}/{vehicleCapacity}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function cell(align: 'left' | 'right'): CSSProperties {
  return { textAlign: align, padding: 'var(--space-1) var(--space-3)', borderBottom: '1px solid var(--border-subtle)' };
}
