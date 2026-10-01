import { useAppActions } from '../state/AppState';

interface BackButtonProps {
  label: string;
  /** True while a job is calculating -- leaving would orphan its result. */
  disabled?: boolean;
}

export function BackButton({ label, disabled = false }: BackButtonProps) {
  const { goBack } = useAppActions();
  return (
    <button
      onClick={goBack}
      disabled={disabled}
      title={disabled ? 'Calculating…' : undefined}
      className="text-caption"
      style={{
        alignSelf: 'flex-start', background: 'var(--bg-surface)',
        color: disabled ? 'var(--border-subtle)' : 'var(--text-secondary)',
        border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
        padding: 'var(--space-2) var(--space-3)',
        cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1,
      }}
    >
      ← {label}
    </button>
  );
}
