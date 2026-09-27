/** Always visible wherever both route colors appear -- never assumes the
 * judge remembers the mapping from a previous screen (Design Brief 6.3). */
export function RouteLegend() {
  return (
    <div className="text-caption" style={{ display: 'flex', gap: 'var(--space-4)' }}>
      <LegendEntry color="var(--route-classical)" dashed={false} label="OR-Tools (classical)" />
      <LegendEntry color="var(--route-quantum)" dashed={true} label="QPSO (quantum-inspired)" />
    </div>
  );
}

function LegendEntry({ color, dashed, label }: { color: string; dashed: boolean; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      <svg width="20" height="8" aria-hidden="true">
        <line
          x1="0" y1="4" x2="20" y2="4"
          stroke={color} strokeWidth="3"
          strokeDasharray={dashed ? '5 3' : undefined}
        />
      </svg>
      {label}
    </span>
  );
}
