import type { AlgorithmResult, RouteChanges } from '../api/types';

interface RouteChangePanelProps {
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
  status: 'none' | 'pending' | 'ready' | 'unavailable';
  depotId?: string;
}

/** Did the accidents make a solver visit stops in a different order? Compares
 * with the same solver run on the accident-free network. The no-accident order
 * is also priced under the accidents, so "saves X min" says whether the new
 * order is actually better, not just different (both solvers are time-limited,
 * so a small difference can occur without the accidents being the cause). */
export function RouteChangePanel({ ortools, qpso, status, depotId }: RouteChangePanelProps) {
  if (status === 'none') return null;

  const name = (id: string) => (id === depotId ? 'Depot' : id);
  const chain = (sequences: string[][]) => sequences.map((s) => s.map(name).join(' → ')).join('  |  ');
  const minutes = (s: number) => (s / 60).toFixed(1);

  function describe(changes: RouteChanges | null | undefined): string {
    if (!changes) return '—';
    if (!changes.changed) return 'same stop order as without accidents';
    if (changes.saved_time_s > 0) {
      return (
        `stop order changed. Without accidents: ${chain(changes.baseline_sequences)} ` +
        `(would now take ${minutes(changes.baseline_time_under_accidents_s)} min); ` +
        `new order takes ${minutes(changes.actual_time_s)} min, saving ${minutes(changes.saved_time_s)} min`
      );
    }
    return (
      `stop order differs from the no-accident run (${chain(changes.baseline_sequences)}) ` +
      'but is not faster under these accidents'
    );
  }

  return (
    <section data-testid="route-changes" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <h2 className="text-body" style={{ fontWeight: 600 }}>Effect on route order</h2>
      {status === 'pending' && <span className="text-caption">Comparing with the no-accident routes…</span>}
      {status === 'unavailable' && <span className="text-caption">No-accident comparison unavailable for this run.</span>}
      {status === 'ready' &&
        [['OR-Tools', ortools], ['QPSO', qpso]].map(([label, result]) => (
          <span key={label as string} className="text-caption">
            {label as string}: {describe((result as AlgorithmResult).route_changes)}
          </span>
        ))}
    </section>
  );
}
