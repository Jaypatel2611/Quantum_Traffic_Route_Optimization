import { describe, it, expect, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { AppStateProvider, useAppActions, useAppState } from '../state/AppState';
import { SetupScreen } from './SetupScreen';

// No WebGL in jsdom; the map itself is covered by the real-browser check.
vi.mock('../components/LazyMapCanvas', () => ({
  MapCanvas: (props: { selectedEdgeIds?: string[]; nodes: unknown[] }) => (
    <div data-testid="map" data-accidents={(props.selectedEdgeIds ?? []).join(',')} data-nodes={props.nodes.length} />
  ),
}));
vi.mock('../api/client', () => ({
  fetchCities: vi.fn().mockResolvedValue([{ id: 'c1', name: 'City One' }]),
  fetchEdges: vi.fn().mockResolvedValue([]),
  createJob: vi.fn(),
}));

let actions: ReturnType<typeof useAppActions>;
let state: ReturnType<typeof useAppState>;
function Probe() {
  actions = useAppActions();
  state = useAppState();
  return null;
}

function setup() {
  render(
    <AppStateProvider>
      <Probe />
      <SetupScreen />
    </AppStateProvider>,
  );
}

describe('SetupScreen multiple accidents', () => {
  it('lists every accident, removes one at a time, then clears all', async () => {
    setup();
    await screen.findByText('City One');
    act(() =>
      actions.updateSetup({
        accidentEdges: [
          { fromNodeId: 1, toNodeId: 2 },
          { fromNodeId: 9, toNodeId: 4 },
          { fromNodeId: 7, toNodeId: 8 },
        ],
      }),
    );

    expect(screen.getByText('3 active accidents')).toBeInTheDocument();
    expect(screen.getByTestId('map')).toHaveAttribute('data-accidents', '1_2,4_9,7_8');

    fireEvent.click(screen.getByLabelText('Remove accident 2'));
    expect(screen.getByText('2 active accidents')).toBeInTheDocument();
    expect(screen.getByTestId('map')).toHaveAttribute('data-accidents', '1_2,7_8');
    expect(state.setup.accidentEdges).toEqual([
      { fromNodeId: 1, toNodeId: 2 },
      { fromNodeId: 7, toNodeId: 8 },
    ]);

    fireEvent.click(screen.getByText('Clear all'));
    expect(screen.queryByTestId('accident-list')).toBeNull();
    expect(state.setup.accidentEdges).toEqual([]);
  });

  it('plots every CSV node on the map and lists them with their demands', async () => {
    setup();
    await screen.findByText('City One');
    // default 5-node scenario: depot + n1..n4
    expect(screen.getByTestId('map')).toHaveAttribute('data-nodes', '5');
    fireEvent.click(screen.getByText(/Nodes \(5\)/));
    expect(screen.getByText('depot (depot)')).toBeInTheDocument();
    expect(screen.getByText('n2')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
  });

  it('keeps the same accidents and nodes when Setup is re-mounted (Back navigation)', async () => {
    const { unmount } = render(
      <AppStateProvider>
        <Probe />
        <SetupScreen />
      </AppStateProvider>,
    );
    unmount();
    // Re-mount inside ONE provider to prove state lives in AppState, not in the screen.
    function Harness() {
      const { screen: current } = useAppState();
      const { goTo } = useAppActions();
      return (
        <>
          <button onClick={() => goTo('results')}>away</button>
          {current === 'setup' && <SetupScreen />}
        </>
      );
    }
    render(
      <AppStateProvider>
        <Probe />
        <Harness />
      </AppStateProvider>,
    );
    await screen.findByText('City One');
    act(() => actions.updateSetup({ accidentEdges: [{ fromNodeId: 5, toNodeId: 6 }], numVehicles: 4 }));
    fireEvent.click(screen.getByText('away'));
    expect(screen.queryByText('City / Network Setup')).toBeNull();
    act(() => actions.goBack());
    expect(await screen.findByText('1 active accident')).toBeInTheDocument();
    expect(screen.getByDisplayValue('4')).toBeInTheDocument();
  });
});
