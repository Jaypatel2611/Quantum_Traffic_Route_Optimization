import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AccidentImpactPanel } from './AccidentImpactPanel';
import type { AccidentImpact, AlgorithmResult } from '../api/types';

const algo = (accident_impacts?: AccidentImpact[]): AlgorithmResult => ({
  meta: {}, total_co2_kg: 0, total_time_s: 0, routes: [], accident_impacts,
});

describe('AccidentImpactPanel', () => {
  it('renders nothing when there are no accidents', () => {
    const { container } = render(<AccidentImpactPanel ortools={algo([])} qpso={algo(undefined)} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says per accident and solver whether it mattered, with minutes', () => {
    const impacts = (status: AccidentImpact['status'], s: number): AccidentImpact[] => [
      { from_node_id: 9, to_node_id: 4, status, added_time_s: s },
      { from_node_id: 1, to_node_id: 2, status: 'not_on_route', added_time_s: 0 },
    ];
    render(<AccidentImpactPanel ortools={algo(impacts('rerouted', 80))} qpso={algo(impacts('driven_through', 240))} />);

    const [first, second] = screen.getByTestId('accident-impacts').querySelectorAll('div');
    expect(first).toHaveTextContent('Accident 1 · road 4_9');
    expect(first).toHaveTextContent('OR-Tools: rerouted around it, +1.3 min');
    expect(first).toHaveTextContent('QPSO: no faster way around — driven through, +4.0 min');
    expect(second).toHaveTextContent('road 1_2');
    expect(second).toHaveTextContent('OR-Tools: not on any route — no effect');
    expect(second).toHaveTextContent('QPSO: not on any route — no effect');
  });
});
