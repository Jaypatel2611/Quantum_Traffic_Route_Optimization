import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { RouteBreakdown } from './RouteBreakdown';
import type { AlgorithmResult, ScenarioNode } from '../api/types';

// Deliberately NOT sorted by demand or id: the table must show the solver's order.
const nodes: ScenarioNode[] = [
  { id: 'depot', lat: 0, lon: 0, demand: 0 },
  { id: 'n1', lat: 0, lon: 0, demand: 30 },
  { id: 'n2', lat: 0, lon: 0, demand: 40 },
  { id: 'n3', lat: 0, lon: 0, demand: 25 },
];

const result: AlgorithmResult = {
  meta: {},
  total_co2_kg: 1,
  total_time_s: 600,
  routes: [
    {
      vehicle_id: 'v0',
      node_sequence: ['depot', 'n2', 'n3', 'n1', 'depot'],
      total_distance_m: 4000,
      total_time_s: 600,
      stops: [
        { node_id: 'depot', leg_distance_m: 0, leg_time_s: 0, cumulative_distance_m: 0, cumulative_time_s: 0 },
        { node_id: 'n2', leg_distance_m: 1000, leg_time_s: 120, cumulative_distance_m: 1000, cumulative_time_s: 120 },
        { node_id: 'n3', leg_distance_m: 500, leg_time_s: 60, cumulative_distance_m: 1500, cumulative_time_s: 180 },
        { node_id: 'n1', leg_distance_m: 1500, leg_time_s: 240, cumulative_distance_m: 3000, cumulative_time_s: 420 },
        { node_id: 'depot', leg_distance_m: 1000, leg_time_s: 180, cumulative_distance_m: 4000, cumulative_time_s: 600 },
      ],
    },
  ],
};

describe('RouteBreakdown', () => {
  it('shows the solver\'s route order, not a demand- or id-sorted one', () => {
    render(<RouteBreakdown label="OR-Tools" color="blue" result={result} nodes={nodes} vehicleCapacity={100} />);
    expect(screen.getByTestId('route-chain-v0')).toHaveTextContent('v0: Depot → n2 → n3 → n1 → Depot');
  });

  it('shows CSV demand, leg and cumulative distance/time, running load and route totals', () => {
    render(<RouteBreakdown label="OR-Tools" color="blue" result={result} nodes={nodes} vehicleCapacity={100} />);
    const rows = screen.getAllByRole('row');
    // header + 5 stops + footer
    expect(rows).toHaveLength(7);

    const n3Cells = within(rows[3]).getAllByRole('cell').map((c) => c.textContent);
    // #, Node, Demand, Leg km, Leg min, Cum km, Cum min, Load
    expect(n3Cells).toEqual(['2', 'n3', '25', '0.50', '1.0', '1.50', '3.0', '65']);

    const footer = within(rows[6]).getAllByRole('cell').map((c) => c.textContent);
    expect(footer).toEqual(['Route total', '4.00 km', '10.0 min', '95/100']);
  });
});
