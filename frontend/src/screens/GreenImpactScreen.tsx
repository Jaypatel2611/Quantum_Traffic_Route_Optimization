import { useState } from 'react';
import { useAppState } from '../state/appStateHooks';
import { StatCard } from '../components/StatCard';
import { Modal } from '../components/Modal';
import { InfoIcon } from '../components/InfoIcon';
import { BackButton } from '../components/BackButton';

/** Design Brief 6.4 captions "vs. unoptimized nearest-neighbor baseline" --
 * this codebase never built a separate naive/nearest-neighbor solver
 * (out of scope, Phases 1-5 only built OR-Tools + QPSO), so the delta shown
 * here is QPSO vs. the OR-Tools classical baseline, consistent with every
 * other screen's comparison. Stated here rather than silently relabeled. */
export function GreenImpactScreen() {
  const { result } = useAppState();
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);

  if (!result || result.status !== 'done') {
    return (
      <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <BackButton label="Back" />
        <h1 className="text-display">Green Impact Dashboard</h1>
        <p className="text-body">No completed run to report on yet.</p>
      </div>
    );
  }

  const { green_impact: impact } = result;

  return (
    <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <BackButton label="Back to Results" />
      <h1 className="text-display">Green Impact Dashboard</h1>

      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <StatCard
          label="CO2 saved"
          value={`${impact.co2_saved_kg.toFixed(2)} kg`}
          caption={`${impact.co2_reduction_percent.toFixed(1)}% vs. OR-Tools baseline`}
          accentColor="var(--accent-eco)"
        />
        <StatCard
          label="Fuel saved"
          value={`${impact.fuel_saved_liters.toFixed(2)} L`}
          caption="derived from CO2 delta"
          accentColor="var(--accent-eco)"
        />
        <StatCard
          label="Time saved"
          value={`${(impact.time_saved_s / 60).toFixed(1)} min`}
          caption="vs. OR-Tools baseline"
          accentColor="var(--accent-eco)"
        />
      </div>

      <div
        style={{
          background: 'var(--bg-surface)', borderLeft: '3px solid var(--status-warning)',
          borderRadius: 'var(--radius-md)', padding: 'var(--space-4)',
        }}
      >
        <p className="text-caption">
          CO2 figures use the COPERT curve shape with IPCC-default magnitude, European-fleet-calibrated —
          not yet an India-specific (ARAI/CPCB) coefficient. The relative % reduction is the primary
          claim; the absolute kg figure is illustrative.
        </p>
      </div>

      <button
        onClick={() => setAssumptionsOpen(true)}
        className="text-body"
        style={{
          alignSelf: 'flex-start', background: 'none', border: 'none', color: 'var(--text-primary)',
          textDecoration: 'underline', display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
        }}
      >
        Assumptions <InfoIcon />
      </button>

      {assumptionsOpen && (
        <Modal title="Assumptions" onClose={() => setAssumptionsOpen(false)}>
          <p className="text-body">{impact.emission_factor_source}</p>
        </Modal>
      )}
    </div>
  );
}
