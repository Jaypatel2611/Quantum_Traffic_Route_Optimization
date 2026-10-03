import { describe, it, expect, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import type { GraphEdge, ScenarioNode } from '../api/types';

// jsdom has no WebGL: capture what MapCanvas hands to DeckGL instead of drawing it.
let deckProps: {
  layers: { id: string; props: Record<string, any> }[];
  onHover: (info: unknown) => void;
};
vi.mock('@deck.gl/react', () => ({
  DeckGL: (props: typeof deckProps) => {
    deckProps = props;
    return <div data-testid="deck" />;
  },
}));

import { MapCanvas } from './MapCanvas';

const nodes: ScenarioNode[] = [
  { id: 'depot', lat: 12.97, lon: 77.64, demand: 0 },
  { id: 'n1', lat: 12.975, lon: 77.644, demand: 30 },
];
const edges: GraphEdge[] = [
  { edgeId: '1_2', fromNodeId: 1, toNodeId: 2, fromLat: 12.97, fromLon: 77.64, toLat: 12.971, toLon: 77.641, travelTimeS: 5 },
  { edgeId: '3_4', fromNodeId: 3, toNodeId: 4, fromLat: 12.972, fromLon: 77.642, toLat: 12.973, toLon: 77.643, travelTimeS: 5 },
];

const layer = (id: string) => deckProps.layers.find((l) => l.id === id)!;
const accidentIds = () => (layer('accident-edges').props.data as GraphEdge[]).map((e) => e.edgeId);

describe('MapCanvas accident styling', () => {
  it('draws exactly the selected roads in a dedicated layer above the hover hit area', () => {
    const { rerender } = render(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={[]} onEdgeClick={() => {}} />);
    expect(accidentIds()).toEqual([]);

    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2']} onEdgeClick={() => {}} />);
    expect(accidentIds()).toEqual(['1_2']);
    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2', '3_4']} onEdgeClick={() => {}} />);
    expect(accidentIds()).toEqual(['1_2', '3_4']);

    // Order is paint order: the hover highlight (hit area) must be underneath the accident lines.
    const order = deckProps.layers.map((l) => l.id);
    expect(order.indexOf('graph-edges-hit-area')).toBeLessThan(order.indexOf('accident-edges'));
    expect(layer('accident-edges').props.getColor).toEqual([229, 72, 77]);
  });

  it('removing an accident takes it off the map; the base roads stay one neutral color', () => {
    const { rerender } = render(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2', '3_4']} />);
    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['3_4']} />);
    expect(accidentIds()).toEqual(['3_4']);
    expect(layer('graph-edges').props.getColor).toEqual([46, 55, 66]);
  });
});

describe('MapCanvas route layers', () => {
  const route = { vehicle_id: 'v0', node_sequence: ['depot', 'n1', 'depot'], total_distance_m: 0, total_time_s: 0 };

  it('offsets a layer sideways so two solvers sharing a road stay both visible', () => {
    render(
      <MapCanvas
        nodes={nodes}
        routeLayers={[
          { routes: [route], color: [46, 107, 230], dashed: false },
          { routes: [route], color: [232, 135, 30], dashed: true, offset: 1 },
        ]}
      />,
    );
    const solid = deckProps.layers.find((l) => l.id === 'routes-0')!;
    const dashed = deckProps.layers.find((l) => l.id === 'routes-1')!;
    expect(solid.props.getOffset).toBe(0);
    expect(dashed.props.getOffset).toBe(1);
    // the offset needs the extension's offset mode on, solid layers included
    expect(solid.props.extensions[0].opts).toMatchObject({ offset: true, dash: false });
    expect(dashed.props.extensions[0].opts).toMatchObject({ offset: true, dash: true });
  });
});

describe('MapCanvas node hover', () => {
  const hover = (object: unknown) =>
    act(() => deckProps.onHover({ layer: object ? { id: 'nodes' } : null, object, x: 40, y: 50 }));

  it('shows node info while hovering and hides it when the pointer leaves', () => {
    render(<MapCanvas nodes={nodes} nodeNotes={{ n1: 'QPSO: v0 stop 1' }} />);
    expect(screen.queryByRole('tooltip')).toBeNull();

    hover({ ...nodes[1], isDepot: false });
    const tip = screen.getByRole('tooltip');
    expect(tip).toHaveTextContent('Node n1');
    expect(tip).toHaveTextContent('Demand: 30');
    expect(tip).toHaveTextContent('Location: 12.97500, 77.64400');
    expect(tip).toHaveTextContent('QPSO: v0 stop 1');
    expect(tip.style.left).toBe('54px'); // follows the cursor, offset from it

    hover(null);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('also hides when the mouse leaves the map container', () => {
    const { container } = render(<MapCanvas nodes={nodes} />);
    hover({ ...nodes[0], isDepot: true });
    expect(screen.getByRole('tooltip')).toHaveTextContent('depot (depot)');
    fireEvent.mouseLeave(container.firstChild as Element);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
