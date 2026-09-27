import { DeckGL } from '@deck.gl/react';
import { OrthographicView } from '@deck.gl/core';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { PathStyleExtension } from '@deck.gl/extensions';
import { useMemo } from 'react';
import type { Route, ScenarioNode } from '../api/types';

export interface MapRouteLayer {
  routes: Route[];
  color: [number, number, number];
  dashed: boolean;
}

interface MapCanvasProps {
  nodes: ScenarioNode[];
  routeLayers?: MapRouteLayer[];
  heightPx?: number;
}

const METERS_PER_DEG_LAT = 110_540;

/** No basemap tiles (fully-offline constraint, PRD Section 2) -- nodes are
 * projected with a flat equirectangular approximation, accurate enough at
 * single-city scale, and plotted on a blank OrthographicView canvas.
 * Real road-snapped route geometry is not retained by the matrix pipeline
 * (see copert_model.py's own note on this); routes render as straight
 * depot-to-customer-to-depot lines, per the Design Brief's own
 * "line-only routes" assumption. */
function project(lat: number, lon: number, lat0: number, lon0: number): [number, number] {
  const metersPerDegLon = 111_320 * Math.cos((lat0 * Math.PI) / 180);
  return [(lon - lon0) * metersPerDegLon, -(lat - lat0) * METERS_PER_DEG_LAT];
}

export function MapCanvas({ nodes, routeLayers = [], heightPx = 420 }: MapCanvasProps) {
  const { positions, viewState } = useMemo(() => {
    if (nodes.length === 0) {
      return { positions: new Map<string, [number, number]>(), viewState: { target: [0, 0, 0] as [number, number, number], zoom: 0 } };
    }
    const lat0 = nodes.reduce((sum, n) => sum + n.lat, 0) / nodes.length;
    const lon0 = nodes.reduce((sum, n) => sum + n.lon, 0) / nodes.length;
    const positions = new Map(nodes.map((n) => [n.id, project(n.lat, n.lon, lat0, lon0)] as const));
    const xs = [...positions.values()].map((p) => p[0]);
    const ys = [...positions.values()].map((p) => p[1]);
    const spanX = Math.max(...xs) - Math.min(...xs), spanY = Math.max(...ys) - Math.min(...ys);
    const span = Math.max(spanX, spanY, 50); // floor avoids a division blowup on a single-node scenario
    const zoom = Math.log2(heightPx / (span * 1.4));
    return { positions, viewState: { target: [0, 0, 0] as [number, number, number], zoom } };
  }, [nodes, heightPx]);

  const nodeLayer = new ScatterplotLayer({
    id: 'nodes',
    data: nodes.map((n) => ({ ...n, position: positions.get(n.id) ?? [0, 0] })),
    getPosition: (d) => d.position,
    getRadius: (d) => (d.id === 'depot' ? 10 : 6),
    getFillColor: (d) => (d.id === 'depot' ? [237, 239, 242] : [154, 165, 177]),
    radiusUnits: 'pixels',
    pickable: false,
  });

  const routePathLayers = routeLayers.map(
    (layer, i) =>
      new PathLayer({
        id: `routes-${i}`,
        data: layer.routes.map((r) => ({
          path: r.node_sequence.map((id) => positions.get(id) ?? [0, 0]),
        })),
        getPath: (d) => d.path,
        getColor: layer.color,
        getWidth: 3,
        widthUnits: 'pixels',
        getDashArray: layer.dashed ? [6, 4] : [1, 0],
        dashJustified: true,
        extensions: layer.dashed ? [new PathStyleExtension({ dash: true })] : [],
      })
  );

  return (
    <div
      key={nodes.map((n) => n.id).join(',')}
      style={{
        position: 'relative',
        height: heightPx,
        background: 'var(--bg-canvas)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
      }}
    >
      <DeckGL
        views={new OrthographicView()}
        initialViewState={viewState}
        controller={true}
        layers={[...routePathLayers, nodeLayer]}
      />
    </div>
  );
}
