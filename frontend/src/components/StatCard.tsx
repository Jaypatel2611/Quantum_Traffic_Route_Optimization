interface StatCardProps {
  label: string;
  value: string;
  caption?: string;
  accentColor: string;
}

/** Colored left border = which algorithm/context this figure belongs to
 * (Design Brief P2) -- earned here, not decorative: it's the primary
 * color-encoding mechanism the whole app relies on. */
export function StatCard({ label, value, caption, accentColor }: StatCardProps) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
        minWidth: 160,
      }}
    >
      <div className="text-caption">{label}</div>
      <div className="text-stat-lg" style={{ margin: '4px 0' }}>
        {value}
      </div>
      {caption && <div className="text-caption">{caption}</div>}
    </div>
  );
}
