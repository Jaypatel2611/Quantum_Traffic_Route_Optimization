import { describe, it, expect } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { AppStateProvider, useAppActions, useAppState } from './AppState';

const wrapper = ({ children }: { children: ReactNode }) => <AppStateProvider>{children}</AppStateProvider>;

function useBoth() {
  return { state: useAppState(), actions: useAppActions() };
}

describe('AppState navigation', () => {
  it('Back from Results returns to Setup and keeps the CSV, settings and accidents', () => {
    const { result } = renderHook(useBoth, { wrapper });
    const nodes = [
      { id: 'D', lat: 1, lon: 2, demand: 0 },
      { id: 'x', lat: 1.1, lon: 2.1, demand: 9 },
    ];
    const accidentEdges = [
      { fromNodeId: 1, toNodeId: 2 },
      { fromNodeId: 3, toNodeId: 4 },
    ];
    act(() => result.current.actions.updateSetup({ nodes, usingDefault: false, numVehicles: 3, accidentEdges }));
    act(() => result.current.actions.goTo('results'));
    act(() => result.current.actions.goBack());

    expect(result.current.state.screen).toBe('setup');
    expect(result.current.state.setup.nodes).toEqual(nodes);
    expect(result.current.state.setup.numVehicles).toBe(3);
    expect(result.current.state.setup.accidentEdges).toEqual(accidentEdges);
  });

  it('Back from Live Run goes to Setup; Back from Green Impact goes to Results and keeps the result', () => {
    const { result } = renderHook(useBoth, { wrapper });
    act(() => result.current.actions.goTo('live-run'));
    act(() => result.current.actions.goBack());
    expect(result.current.state.screen).toBe('setup');

    act(() => result.current.actions.setResult({ status: 'running' }));
    act(() => result.current.actions.goTo('green-impact'));
    act(() => result.current.actions.goBack());
    expect(result.current.state.screen).toBe('results');
    expect(result.current.state.result).toEqual({ status: 'running' });
  });
});
