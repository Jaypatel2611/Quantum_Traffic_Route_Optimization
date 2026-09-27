import { Modal } from '../components/Modal';
import { FairnessFooter } from '../components/FairnessFooter';

interface HowItWorksModalProps {
  seed: number;
  timeBudgetS: number;
  onClose: () => void;
}

/** Formulas rendered as plain monospace text, not MathJax/KaTeX -- adding a
 * math-typesetting dependency for five static formula blocks in a 36-hour
 * build is disproportionate; Unicode math notation is legible enough for
 * the technically literate judges this screen targets (PRD Section 5). */
export function HowItWorksModal({ seed, timeBudgetS, onClose }: HowItWorksModalProps) {
  return (
    <Modal title="How It Works" onClose={onClose}>
      <p className="text-body">
        QPSO (Quantum-behaved Particle Swarm Optimization) searches for good delivery routes the way a
        swarm of particles explores a landscape, but each particle's next position is drawn from a
        quantum-inspired probability distribution instead of a fixed velocity rule -- letting it
        occasionally "tunnel" past locally-good-but-globally-poor solutions that trap classical swarms.
      </p>

      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, background: 'var(--bg-canvas)', padding: 'var(--space-4)', borderRadius: 'var(--radius-sm)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <div>ROV mapping: permutation = argsort(X), X ∈ R^N</div>
        <div>Attractor: p = φ·pbest + (1-φ)·gbest, φ ~ U(0,1)</div>
        <div>mbest = mean(pbest_1, …, pbest_M)</div>
        <div>Monte Carlo update: x' = p ± α·|mbest - x|·ln(1/u), u ~ U(0,1)</div>
        <div>α-schedule: α(t) = 1 - 0.5·(t / t_max)^k</div>
      </div>

      <p className="text-caption" style={{ marginTop: 'var(--space-4)' }}>
        Reproducibility footer:
      </p>
      <FairnessFooter seed={seed} timeBudgetS={timeBudgetS} ortoolsVersion="9.15.6755" />
    </Modal>
  );
}
