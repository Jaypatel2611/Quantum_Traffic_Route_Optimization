import { describe, it, expect, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { AppStateProvider, useAppActions, useAppState } from '../state/AppState';
import { ResultsScreen } from './ResultsScreen';
import { LiveRunScreen } from './LiveRunScreen';

vi.mock('../components/LazyMapCanvas', () => ({ MapCanvas: () => <div /> }));
vi.mock('../components/LazyConvergenceChart', () => ({ ConvergenceChart: () => <div /> }));
vi.mock('../api/client', () => ({
  fetchEdges: vi.fn().mockResolvedValue([]),
  fetchJobResult: vi.fn(),
  subscribeToConvergence: vi.fn(() => () => {}),
}));

const scenario = {
  cityId: 'c', nodes: [], vehicleCapacity: 10, numVehicles: 1, seed: 1, timeBudgetS: 1, accidentEdges: [],
};

let actions: ReturnType<typeof useAppActions>;
let state: ReturnType<typeof useAppState>;
function Probe() {
  actions = useAppActions();
  state = useAppState();
  return null;
}

describe('Back is disabled while calculating', () => {
  it('Live Run: disabled until the stream completes, then goes back to Setup', () => {
    render(
      <AppStateProvider>
        <Probe />
        <LiveRunScreen />
      </AppStateProvider>,
    );
    act(() => actions.startJob(scenario, 'job-1'));
    const back = screen.getByRole('button', { name: /back to setup/i });
    expect(back).toBeDisabled();
    fireEvent.click(back);
    expect(state.screen).toBe('live-run');

    act(() => actions.markStreamComplete());
    expect(back).toBeEnabled();
    fireEvent.click(back);
    expect(state.screen).toBe('setup');
  });

  it('Results: disabled while the result is still pending, enabled on a solver error', () => {
    render(
      <AppStateProvider>
        <Probe />
        <ResultsScreen />
      </AppStateProvider>,
    );
    act(() => actions.startJob(scenario, 'job-2'));
    act(() => actions.goTo('results'));
    expect(screen.getByRole('button', { name: /back to setup/i })).toBeDisabled();

    act(() => actions.setResult({ status: 'error', detail: 'boom' }));
    expect(screen.getByRole('button', { name: /back to setup/i })).toBeEnabled();
  });
});
