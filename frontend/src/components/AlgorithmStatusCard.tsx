interface AlgorithmStatusCardProps {
  name: string;
  color: string;
  currentBest: string;
  elapsedLabel: string;
}

export function AlgorithmStatusCard({ name, color, currentBest, elapsedLabel }: AlgorithmStatusCardProps) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderLeft: `3px solid ${color}`,
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
        flex: 1,
      }}
    >
      <div className="text-body">{name}</div>
      <div className="text-stat-lg">{currentBest}</div>
      <div className="text-caption">{elapsedLabel}</div>
    </div>
  );
}
