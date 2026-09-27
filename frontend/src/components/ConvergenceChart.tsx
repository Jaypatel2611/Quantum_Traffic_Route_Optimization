import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface ConvergenceChartProps {
  history: number[];
}

/** QPSO is the only solver that streams incremental progress (Section 6.2)
 * -- OR-Tools' AlgorithmStatusCard shows elapsed time only, no chart line,
 * since it optimizes internally and reports a single final result. */
/** A small/trivial instance converges to a near-constant fitness within the
 * first few iterations and stays flush there for the rest of the run --
 * real convergence, but with no y-padding the line sits exactly on the axis
 * and reads as an empty chart. Padding the domain keeps a flat series
 * visibly drawn above the axis instead of invisible on top of it. */
function paddedDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * 0.15, 0.05);
  return [min - pad, max + pad];
}

export function ConvergenceChart({ history }: ConvergenceChartProps) {
  const data = history.map((gbest, iteration) => ({ iteration, gbest }));
  const domain = paddedDomain(history);

  return (
    <div className="text-h2" style={{ color: 'var(--text-primary)' }}>
      <h2 className="text-h2">Convergence</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
          <XAxis
            dataKey="iteration"
            stroke="var(--text-secondary)"
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 12, fill: 'var(--text-secondary)' }}
            label={{ value: 'iteration', position: 'insideBottom', offset: -4, fill: 'var(--text-secondary)', fontSize: 12 }}
          />
          <YAxis
            domain={domain}
            stroke="var(--text-secondary)"
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 12, fill: 'var(--text-secondary)' }}
            label={{ value: 'gbest fitness', angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{ background: 'var(--bg-surface-raised)', border: '1px solid var(--border-subtle)', borderRadius: 6 }}
            labelStyle={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}
            itemStyle={{ color: 'var(--route-quantum)', fontFamily: 'var(--font-mono)' }}
          />
          <Line
            type="monotone"
            dataKey="gbest"
            stroke="var(--route-quantum)"
            strokeDasharray="6 4"
            dot={false}
            isAnimationActive={false}
          />
          {data.length > 0 && (
            <ReferenceDot
              x={data[data.length - 1].iteration}
              y={data[data.length - 1].gbest}
              r={4}
              fill="var(--route-quantum)"
              stroke="var(--bg-canvas)"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
