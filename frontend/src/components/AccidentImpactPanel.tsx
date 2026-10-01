import type { AccidentImpact, AlgorithmResult } from '../api/types';

interface AccidentImpactPanelProps {
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
}

const roadId = (a: AccidentImpact) => `${Math.min(a.from_node_id, a.to_node_id)}_${Math.max(a.from_node_id, a.to_node_id)}`;

function describe(impact: AccidentImpact): string {
  const minutes = (impact.added_time_s / 60).toFixed(1);
  switch (impact.status) {
    case 'not_on_route':
      return 'not on any route — no effect';
    case 'rerouted':
      return `rerouted around it, +${minutes} min`;
    default:
      return `no faster way around — driven through, +${minutes} min`;
  }
}

/** Per accident and solver: did it matter? Without this, an accident on a dead
 * end (or one the solver already routed away from) looks like a bug. Times
 * are base road time; the random traffic delay is not attributed per road. */
export function AccidentImpactPanel({ ortools, qpso }: AccidentImpactPanelProps) {
  const solvers = [
    { label: 'OR-Tools', impacts: ortools.accident_impacts ?? [] },
    { label: 'QPSO', impacts: qpso.accident_impacts ?? [] },
  ];
  const accidents = solvers[0].impacts;
  if (accidents.length === 0) return null;

  return (
    <section data-testid="accident-impacts" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <h2 className="text-body" style={{ fontWeight: 600 }}>Accident impact</h2>
      {accidents.map((accident, i) => (
        <div key={roadId(accident)} className="text-caption" style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
          <span style={{ color: 'var(--status-error)', fontWeight: 600 }}>Accident {i + 1} · road {roadId(accident)}</span>
          {solvers.map(({ label, impacts }) => (
            <span key={label}>
              {label}: {impacts[i] ? describe(impacts[i]) : '—'}
            </span>
          ))}
        </div>
      ))}
    </section>
  );
}
