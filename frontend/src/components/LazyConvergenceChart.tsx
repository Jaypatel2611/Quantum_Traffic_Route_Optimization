import { lazy, Suspense } from 'react';
import type { ComponentProps } from 'react';
import type { ConvergenceChart as ConvergenceChartType } from './ConvergenceChart';

// Recharts is the second-largest dependency in the bundle; only the Live
// Run screen renders a chart. Split into its own chunk, loaded only when
// that screen actually mounts.
const ConvergenceChartLazy = lazy(() =>
  import('./ConvergenceChart').then((m) => ({ default: m.ConvergenceChart }))
);

export function ConvergenceChart(props: ComponentProps<typeof ConvergenceChartType>) {
  return (
    <Suspense fallback={<div style={{ height: 280 }} />}>
      <ConvergenceChartLazy {...props} />
    </Suspense>
  );
}
