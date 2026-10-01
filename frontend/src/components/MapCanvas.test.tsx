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
  { edgeId: '1_2', fromNodeId: 1, toNodeId: 2, fromLat: 12.97, fromLon: 77.64, toLat: 12.971, toLon: 77.641 },
  { edgeId: '3_4', fromNodeId: 3, toNodeId: 4, fromLat: 12.972, fromLon: 77.642, toLat: 12.973, toLon: 77.643 },
];

const edgeLayer = () => deckProps.layers.find((l) => l.id === 'graph-edges')!;

describe('MapCanvas accident styling', () => {
  it('re-triggers the red/dashed styling every time the selection changes', () => {
    const { rerender } = render(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={[]} />);
    const none = edgeLayer().props.updateTriggers.getColor;

    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2']} />);
    const one = edgeLayer().props.updateTriggers.getColor;
    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2', '3_4']} />);
    const two = edgeLayer().props.updateTriggers.getColor;

    // deck.gl diffs trigger values shallowly: they must be primitives that differ
    // (two Sets would always compare equal and never refresh the colors).
    expect(typeof one).toBe('string');
    expect(new Set([none, one, two]).size).toBe(3);
    expect(edgeLayer().props.getColor(edges[0])).toEqual([229, 72, 77]);
    expect(edgeLayer().props.getColor(edges[1])).toEqual([229, 72, 77]);
  });

  it('removing an accident restores the normal road color', () => {
    const { rerender } = render(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['1_2', '3_4']} />);
    rerender(<MapCanvas nodes={nodes} edges={edges} selectedEdgeIds={['3_4']} />);
    expect(edgeLayer().props.getColor(edges[0])).toEqual([46, 55, 66]);
    expect(edgeLayer().props.getColor(edges[1])).toEqual([229, 72, 77]);
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
