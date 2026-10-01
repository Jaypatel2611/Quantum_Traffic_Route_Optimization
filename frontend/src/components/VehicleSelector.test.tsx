import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { VehicleSelector } from './VehicleSelector';
import { routeKey, vehicleColor } from '../utils/vehicleColor';
import type { AlgorithmResult } from '../api/types';

const algo = (ids: string[]): AlgorithmResult => ({
  meta: {},
  total_co2_kg: 0,
  total_time_s: 0,
  routes: ids.map((id) => ({ vehicle_id: id, node_sequence: ['depot', id, 'depot'], total_distance_m: 0, total_time_s: 0 })),
});

describe('VehicleSelector', () => {
  const ortools = algo(['v0', 'v1']);
  const qpso = algo(['v0', 'v1', 'v2']);

  it('lists every vehicle of both solvers, all pressed by default', () => {
    render(<VehicleSelector ortools={ortools} qpso={qpso} visible={null} onChange={() => {}} />);
    const chips = screen.getAllByRole('button', { pressed: true });
    expect(chips).toHaveLength(5);
  });

  it('toggling one vehicle off shows only the rest; toggling the last back returns to "all"', () => {
    const onChange = vi.fn();
    const { rerender } = render(<VehicleSelector ortools={ortools} qpso={qpso} visible={null} onChange={onChange} />);

    fireEvent.click(screen.getAllByText('v1')[0]); // OR-Tools v1
    expect(onChange).toHaveBeenLastCalledWith(['ortools:v0', 'qpso:v0', 'qpso:v1', 'qpso:v2']);

    rerender(
      <VehicleSelector ortools={ortools} qpso={qpso} visible={['ortools:v0', 'qpso:v0', 'qpso:v1', 'qpso:v2']} onChange={onChange} />,
    );
    fireEvent.click(screen.getAllByText('v1')[0]);
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it('"All" resets the filter', () => {
    const onChange = vi.fn();
    render(<VehicleSelector ortools={ortools} qpso={qpso} visible={['qpso:v2']} onChange={onChange} />);
    fireEvent.click(screen.getByText('All'));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});

describe('vehicleColor', () => {
  it('first vehicle keeps the solver\'s reserved color; the rest differ from it and each other', () => {
    expect(vehicleColor('ortools', 0)).toEqual([46, 107, 230]);
    expect(vehicleColor('qpso', 0)).toEqual([232, 135, 30]);
    const shades = [0, 1, 2, 3].map((i) => vehicleColor('ortools', i).join(','));
    expect(new Set(shades).size).toBe(4);
    expect(routeKey('qpso', 'v1')).toBe('qpso:v1');
  });
});
