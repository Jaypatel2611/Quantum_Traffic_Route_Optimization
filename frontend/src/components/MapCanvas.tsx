import { DeckGL } from '@deck.gl/react';
import { OrthographicView } from '@deck.gl/core';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { PathStyleExtension } from '@deck.gl/extensions';
import { useCallback, useMemo, useState } from 'react';
import type { GraphEdge, Route, ScenarioNode } from '../api/types';
import { colorForNode } from '../utils/nodeColor';

export interface MapRouteLayer {
  routes: Route[];
  /** Layer color; routes[i] uses colors[i] when given (one shade per vehicle). */
  color: [number, number, number];
  colors?: [number, number, number][];
  dashed: boolean;
  /** Sideways shift in line widths (right of travel direction when positive), so
   * two solvers sharing a road draw side by side instead of one hiding the other. */
  offset?: number;
}

interface HoveredNode {
  node: ScenarioNode;
  isDepot: boolean;
  x: number;
  y: number;
}

interface MapCanvasProps {
  nodes: ScenarioNode[];
  routeLayers?: MapRouteLayer[];
  heightPx?: number;
  /** Flow C: road segments the accident-injection toggle lets a user pick
   * from. Rendered as thin lines; onEdgeClick fires when one is clicked. */
  edges?: GraphEdge[];
  /** Accident road segments -- every one is drawn red/dashed. */
  selectedEdgeIds?: string[];
  onEdgeClick?: (edge: GraphEdge) => void;
  /** [lat, lon] road legs the accidents forced onto a detour, drawn as a
   * yellow halo under the route lines. */
  reroutedPaths?: [number, number][][];
  /** Extra tooltip line per node id (e.g. which route visits it, and when). */
  nodeNotes?: Record<string, string>;
}

const METERS_PER_DEG_LAT = 110_540;

/** No basemap tiles (fully-offline constraint, PRD Section 2) -- nodes are
 * projected with a flat equirectangular approximation, accurate enough at
 * single-city scale, and plotted on a blank OrthographicView canvas.
 * Routes follow the road network via the backend's per-route `geometry`
 * polyline; a route without one (raw-matrix jobs) falls back to straight
 * stop-to-stop lines. */
function project(lat: number, lon: number, lat0: number, lon0: number): [number, number] {
  const metersPerDegLon = 111_320 * Math.cos((lat0 * Math.PI) / 180);
  return [(lon - lon0) * metersPerDegLon, -(lat - lat0) * METERS_PER_DEG_LAT];
}

const NO_IDS: string[] = [];
const NO_PATHS: [number, number][][] = [];
const NO_NOTES: Record<string, string> = {};

export function MapCanvas({
  nodes, routeLayers = [], heightPx = 420, edges = [], selectedEdgeIds = NO_IDS, onEdgeClick,
  reroutedPaths = NO_PATHS, nodeNotes = NO_NOTES,
}: MapCanvasProps) {
  const selectedSet = useMemo(() => new Set(selectedEdgeIds), [selectedEdgeIds]);
  const [hovered, setHovered] = useState<HoveredNode | null>(null);
  const { positions, viewState, lat0, lon0 } = useMemo(() => {
    if (nodes.length === 0) {
      return {
        positions: new Map<string, [number, number]>(),
        viewState: { target: [0, 0, 0] as [number, number, number], zoom: 0 },
        lat0: 0, lon0: 0,
      };
    }
    const lat0 = nodes.reduce((sum, n) => sum + n.lat, 0) / nodes.length;
    const lon0 = nodes.reduce((sum, n) => sum + n.lon, 0) / nodes.length;
    const positions = new Map(nodes.map((n) => [n.id, project(n.lat, n.lon, lat0, lon0)] as const));
    const xs = [...positions.values()].map((p) => p[0]);
    const ys = [...positions.values()].map((p) => p[1]);
    const spanX = Math.max(...xs) - Math.min(...xs), spanY = Math.max(...ys) - Math.min(...ys);
    const span = Math.max(spanX, spanY, 50); // floor avoids a division blowup on a single-node scenario
    const zoom = Math.log2(heightPx / (span * 1.4));
    return { positions, viewState: { target: [0, 0, 0] as [number, number, number], zoom }, lat0, lon0 };
  }, [nodes, heightPx]);

  const edgePath = useCallback(
    (e: GraphEdge): [number, number][] => [
      project(e.fromLat, e.fromLon, lat0, lon0),
      project(e.toLat, e.toLon, lat0, lon0),
    ],
    [lat0, lon0]
  );

  const edgeLayers = useMemo(() => {
    if (edges.length === 0) return [];
    const base = new PathLayer({
      id: 'graph-edges',
      data: edges,
      getPath: edgePath,
      getColor: [46, 55, 66],
      getWidth: 1.5,
      widthUnits: 'pixels',
      pickable: false,
    });
    // Accident roads are their own layer, drawn above the hover band, with the
    // selected edges as *data* (not an accessor trigger): a newly picked road
    // used to stay hidden under the hit area's yellow hover highlight until the
    // pointer moved away.
    const accidents = new PathLayer({
      id: 'accident-edges',
      data: edges.filter((e) => selectedSet.has(e.edgeId)),
      getPath: edgePath,
      getColor: [229, 72, 77],
      getWidth: 5,
      getDashArray: [6, 4],
      dashJustified: true,
      extensions: [new PathStyleExtension({ dash: true })],
      widthUnits: 'pixels',
      pickable: false,
      parameters: { depthCompare: 'always' },
    });
    if (!onEdgeClick) return [base, accidents];
    // A 1.5px line is very hard to actually click -- a wide, effectively
    // invisible sibling layer gives it a real hit area without changing
    // what's drawn. Standard deck.gl pattern for thin-line picking.
    const hitArea = new PathLayer({
      id: 'graph-edges-hit-area',
      data: edges,
      getPath: edgePath,
      getColor: [0, 0, 0, 1],
      getWidth: 16,
      widthUnits: 'pixels',
      pickable: true,
      autoHighlight: true,
      highlightColor: [242, 201, 76, 100],
      onClick: (info: { object?: GraphEdge }) => info.object && onEdgeClick(info.object),
    });
    return [hitArea, base, accidents];
  }, [edges, edgePath, selectedSet, onEdgeClick]);

  // The CSV's first row is the depot (node_ids[0], this codebase's convention),
  // whatever its id string is.
  const nodeLayer = new ScatterplotLayer({
    id: 'nodes',
    data: nodes.map((n, i) => ({ ...n, isDepot: i === 0, position: positions.get(n.id) ?? [0, 0] })),
    getPosition: (d) => d.position,
    getRadius: (d) => (d.isDepot ? 10 : 7),
    getFillColor: (d) => (d.isDepot ? [237, 239, 242] : colorForNode(d.id)),
    getLineColor: (d) => (d.isDepot ? [237, 239, 242] : [18, 22, 28]),
    lineWidthMinPixels: 1,
    stroked: true,
    radiusUnits: 'pixels',
    pickable: true,
  });

  const reroutedLayer = new PathLayer({
    id: 'rerouted-halo',
    data: reroutedPaths,
    getPath: (leg: [number, number][]) => leg.map(([lat, lon]) => project(lat, lon, lat0, lon0)),
    getColor: [242, 201, 76, 210],
    getWidth: 9,
    widthUnits: 'pixels',
    capRounded: true,
    jointRounded: true,
  });

  const routePathLayers = routeLayers.map(
    (layer, i) =>
      new PathLayer({
        id: `routes-${i}`,
        data: layer.routes.map((r, j) => ({
          color: layer.colors?.[j] ?? layer.color,
          path: r.geometry
            ? r.geometry.map(([lat, lon]) => project(lat, lon, lat0, lon0))
            : r.node_sequence.map((id) => positions.get(id) ?? [0, 0]),
        })),
        getPath: (d) => d.path,
        getColor: (d) => d.color,
        getWidth: 3,
        widthUnits: 'pixels',
        getDashArray: layer.dashed ? [6, 4] : [1, 0],
        getOffset: layer.offset ?? 0,
        dashJustified: true,
        extensions: [new PathStyleExtension({ dash: layer.dashed, offset: true })],
      })
  );

  return (
    <div
      key={nodes.map((n) => n.id).join(',')}
      onDragStart={(e) => e.preventDefault()}
      onMouseLeave={() => setHovered(null)}
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
        layers={[...edgeLayers, reroutedLayer, ...routePathLayers, nodeLayer]}
        onHover={(info) => {
          if (info.layer?.id === 'nodes' && info.object) {
            const n = info.object as ScenarioNode & { isDepot: boolean };
            setHovered({ node: n, isDepot: n.isDepot, x: info.x, y: info.y });
          } else {
            setHovered(null);
          }
        }}
        getCursor={({ isHovering }) => (onEdgeClick && isHovering ? 'pointer' : 'grab')}
      />
      {hovered && (
        <div
          role="tooltip"
          style={{
            position: 'absolute', left: hovered.x + 14, top: hovered.y + 14, pointerEvents: 'none',
            background: 'var(--bg-surface-raised)', color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-2) var(--space-3)', whiteSpace: 'pre', fontSize: 12, zIndex: 2,
          }}
        >
          {/* React text, not HTML: node ids come straight from the user's CSV. */}
          {[
            hovered.isDepot ? `${hovered.node.id} (depot)` : `Node ${hovered.node.id}`,
            `Demand: ${hovered.node.demand}`,
            `Location: ${hovered.node.lat.toFixed(5)}, ${hovered.node.lon.toFixed(5)}`,
            ...(nodeNotes[hovered.node.id] ? [nodeNotes[hovered.node.id]] : []),
          ].join('\n')}
        </div>
      )}
      <span
        className="text-caption"
        style={{
          position: 'absolute', bottom: 4, right: 8,
          color: 'var(--text-secondary, #9aa5b1)', pointerEvents: 'none',
        }}
      >
        © OpenStreetMap contributors
      </span>
    </div>
  );
}
