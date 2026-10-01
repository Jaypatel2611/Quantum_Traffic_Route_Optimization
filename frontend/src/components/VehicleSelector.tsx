import type { AlgorithmResult } from '../api/types';
import { routeKey, vehicleColor, type Solver } from '../utils/vehicleColor';

interface VehicleSelectorProps {
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
  /** Keys from routeKey(); null means every vehicle is shown. */
  visible: string[] | null;
  onChange: (visible: string[] | null) => void;
}

const SOLVERS: { solver: Solver; label: string }[] = [
  { solver: 'ortools', label: 'OR-Tools' },
  { solver: 'qpso', label: 'QPSO' },
];

/** One toggle per vehicle per solver, so each vehicle's road path can be
 * viewed on its own (or compared with any others). */
export function VehicleSelector({ ortools, qpso, visible, onChange }: VehicleSelectorProps) {
  const results = { ortools, qpso };
  const all = SOLVERS.flatMap(({ solver }) => results[solver].routes.map((r) => routeKey(solver, r.vehicle_id)));
  const shown = new Set(visible ?? all);

  function toggle(key: string) {
    const next = new Set(shown);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onChange(next.size === all.length ? null : all.filter((k) => next.has(k)));
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }} data-testid="vehicle-selector">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <span className="text-caption">Vehicles shown</span>
        <button onClick={() => onChange(null)} disabled={visible === null} className="text-caption" style={chip(false)}>
          All
        </button>
      </div>
      {SOLVERS.map(({ solver, label }) => (
        <div key={solver} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span className="text-caption" style={{ minWidth: 70 }}>{label}</span>
          {results[solver].routes.map((route, i) => {
            const key = routeKey(solver, route.vehicle_id);
            const [r, g, b] = vehicleColor(solver, i);
            const on = shown.has(key);
            return (
              <button
                key={key}
                onClick={() => toggle(key)}
                aria-pressed={on}
                className="text-caption"
                style={chip(on)}
              >
                <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: `rgb(${r},${g},${b})`, marginRight: 6, opacity: on ? 1 : 0.35 }} />
                {route.vehicle_id}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function chip(on: boolean) {
  return {
    background: on ? 'var(--bg-surface-raised)' : 'var(--bg-surface)',
    color: on ? 'var(--text-primary)' : 'var(--text-secondary)',
    border: `1px solid ${on ? 'var(--text-secondary)' : 'var(--border-subtle)'}`,
    borderRadius: 'var(--radius-sm)', padding: '2px 10px',
  } as const;
}
