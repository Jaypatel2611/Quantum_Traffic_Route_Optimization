interface FairnessFooterProps {
  seed: number;
  timeBudgetS: number;
  ortoolsVersion?: string;
}

/** Reproducibility proof point (PRD Section 7/15, Design Brief 6.2/6.5) --
 * shown on both the Live Run screen and the How It Works modal. */
export function FairnessFooter({ seed, timeBudgetS, ortoolsVersion }: FairnessFooterProps) {
  return (
    <div
      className="text-caption"
      style={{ fontFamily: 'var(--font-mono)', display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}
    >
      <span>seed: #{seed}</span>
      <span>time budget: {timeBudgetS.toFixed(1)}s</span>
      {ortoolsVersion && <span>OR-Tools: {ortoolsVersion}</span>}
    </div>
  );
}
