import { useEffect } from 'react';
import { fetchJobResult, subscribeToConvergence } from '../api/client';
import { useAppActions, useAppState } from '../state/AppState';
import { ConvergenceChart } from '../components/ConvergenceChart';
import { AlgorithmStatusCard } from '../components/AlgorithmStatusCard';
import { FairnessFooter } from '../components/FairnessFooter';
import { InfoIcon } from '../components/InfoIcon';
import { HowItWorksModal } from './HowItWorksModal';

export function LiveRunScreen() {
  const { jobId, scenario, convergenceHistory, streamComplete, streamError, howItWorksOpen } = useAppState();
  const { appendProgress, markStreamComplete, markStreamError, setResult, goTo, setHowItWorksOpen } = useAppActions();

  useEffect(() => {
    if (!jobId) return;
    const unsubscribe = subscribeToConvergence(jobId, {
      onProgress: appendProgress,
      onComplete: () => {
        markStreamComplete();
        fetchJobResult(jobId).then(setResult);
      },
      onError: markStreamError,
    });
    return unsubscribe;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  if (!scenario) return null;

  const currentBest = convergenceHistory.length > 0 ? convergenceHistory[convergenceHistory.length - 1] : null;

  return (
    <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="text-display">Live Optimization Run</h1>
          <FairnessFooter seed={scenario.seed} timeBudgetS={scenario.timeBudgetS} />
        </div>
        <button
          onClick={() => setHowItWorksOpen(true)}
          style={{
            background: 'var(--bg-surface)', color: 'var(--text-secondary)',
            border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-2) var(--space-3)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
          }}
        >
          How It Works <InfoIcon />
        </button>
      </div>

      {streamError && (
        <div style={{ background: 'var(--status-error)', color: 'var(--bg-canvas)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)' }} role="alert">
          Solver error: {streamError}
        </div>
      )}

      <ConvergenceChart history={convergenceHistory} />

      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <AlgorithmStatusCard
          name="OR-Tools (classical)"
          color="var(--route-classical)"
          currentBest={streamComplete ? 'done' : 'running…'}
          elapsedLabel={`time budget ${scenario.timeBudgetS.toFixed(1)}s`}
        />
        <AlgorithmStatusCard
          name="QPSO (quantum-inspired)"
          color="var(--route-quantum)"
          currentBest={currentBest !== null ? currentBest.toFixed(4) : '—'}
          elapsedLabel={`${convergenceHistory.length} iterations streamed`}
        />
      </div>

      <button
        onClick={() => goTo('results')}
        disabled={!streamComplete || !!streamError}
        title={streamComplete ? undefined : 'waiting for both solvers'}
        className={streamComplete ? 'pulse-once' : undefined}
        style={{
          alignSelf: 'flex-start', padding: 'var(--space-3) var(--space-6)',
          background: streamComplete ? 'var(--text-primary)' : 'var(--bg-surface-raised)',
          color: streamComplete ? 'var(--bg-canvas)' : 'var(--text-secondary)',
          border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 600,
        }}
      >
        View Results
      </button>

      {howItWorksOpen && (
        <HowItWorksModal
          seed={scenario.seed}
          timeBudgetS={scenario.timeBudgetS}
          onClose={() => setHowItWorksOpen(false)}
        />
      )}
    </div>
  );
}
