import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RouteChangePanel } from './RouteChangePanel';
import type { AlgorithmResult, RouteChanges } from '../api/types';

const algo = (route_changes?: RouteChanges): AlgorithmResult => ({
  meta: {}, total_co2_kg: 0, total_time_s: 0, routes: [], route_changes,
});

const changed = (saved: number): RouteChanges => ({
  changed: true,
  baseline_sequences: [['depot', 'n1', 'n2', 'depot']],
  baseline_time_under_accidents_s: 600,
  actual_time_s: 600 - saved,
  saved_time_s: saved,
});
const same: RouteChanges = { ...changed(0), changed: false };

describe('RouteChangePanel', () => {
  it('renders nothing when there are no accidents', () => {
    const { container } = render(<RouteChangePanel ortools={algo()} qpso={algo()} status="none" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says it is comparing while the baseline is still solving', () => {
    render(<RouteChangePanel ortools={algo()} qpso={algo()} status="pending" />);
    expect(screen.getByText('Comparing with the no-accident routes…')).toBeInTheDocument();
  });

  it('says so when the comparison could not be made', () => {
    render(<RouteChangePanel ortools={algo()} qpso={algo()} status="unavailable" />);
    expect(screen.getByText(/unavailable for this run/)).toBeInTheDocument();
  });

  it('reports unchanged, improved and merely-different orders per solver', () => {
    render(
      <RouteChangePanel ortools={algo(same)} qpso={algo(changed(120))} status="ready" depotId="depot" />,
    );
    const panel = screen.getByTestId('route-changes');
    expect(panel).toHaveTextContent('OR-Tools: same stop order as without accidents');
    expect(panel).toHaveTextContent('Without accidents: Depot → n1 → n2 → Depot');
    expect(panel).toHaveTextContent('would now take 10.0 min');
    expect(panel).toHaveTextContent('new order takes 8.0 min, saving 2.0 min');
  });

  it('does not claim a gain when the different order is not faster', () => {
    render(<RouteChangePanel ortools={algo(changed(-30))} qpso={algo(same)} status="ready" depotId="depot" />);
    expect(screen.getByTestId('route-changes')).toHaveTextContent('differs from the no-accident run');
    expect(screen.getByTestId('route-changes')).toHaveTextContent('not faster under these accidents');
    expect(screen.getByTestId('route-changes')).not.toHaveTextContent('saving');
  });
});
