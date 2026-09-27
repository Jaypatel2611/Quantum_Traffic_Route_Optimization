import { lazy, Suspense } from 'react';
import type { ComponentProps } from 'react';
import type { MapCanvas as MapCanvasType } from './MapCanvas';

// Deck.GL is the single largest dependency in the bundle (WebGL + layers +
// extensions) but only Setup and Results actually render a map -- Live Run
// and Green Impact pay for it too under a single eager import. Splitting it
// into its own chunk, loaded only when a map screen actually mounts.
const MapCanvasLazy = lazy(() => import('./MapCanvas').then((m) => ({ default: m.MapCanvas })));

export function MapCanvas(props: ComponentProps<typeof MapCanvasType>) {
  return (
    <Suspense fallback={<div style={{ height: props.heightPx ?? 420 }} />}>
      <MapCanvasLazy {...props} />
    </Suspense>
  );
}
