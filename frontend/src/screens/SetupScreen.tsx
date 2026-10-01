import { useEffect, useState } from 'react';
import { createJob, fetchCities, fetchEdges } from '../api/client';
import type { City, GraphEdge, ScenarioNode } from '../api/types';
import { useAppActions, useAppState } from '../state/AppState';
import { MapCanvas } from '../components/LazyMapCanvas';
import { MapLegend } from '../components/MapLegend';
import { NodeTable } from '../components/NodeTable';

const CSV_TEMPLATE = 'node_id,lat,lon,demand\ndepot,12.9716,77.6412,0\nn1,12.9750,77.6440,30\n';

/** Must match the backend's own `f"{min(u,v)}_{max(u,v)}"` convention
 * (cached_graph_repository.py's list_edges) exactly, order-independent --
 * this is the only thing that lets the selected edge highlight itself on
 * the map after being picked. */
export function edgeIdFor(a: number, b: number): string {
  return `${Math.min(a, b)}_${Math.max(a, b)}`;
}

/** Template's own documented assumption (not in the PRD's schema, which
 * left this undefined): the CSV's first data row is the depot -- matches
 * this codebase's existing node_ids[0]="depot" convention throughout. */
export function parseNodesCsv(text: string): ScenarioNode[] {
  const lines = text.trim().split(/\r?\n/);
  const [header, ...rows] = lines;
  const columns = header.split(',').map((c) => c.trim().toLowerCase());
  const idx = {
    id: columns.indexOf('node_id'),
    lat: columns.indexOf('lat'),
    lon: columns.indexOf('lon'),
    demand: columns.indexOf('demand'),
  };
  if (idx.id === -1 || idx.lat === -1 || idx.lon === -1 || idx.demand === -1) {
    throw new Error('CSV must have columns: node_id, lat, lon, demand');
  }
  const nodes = rows
    .filter((row) => row.trim().length > 0)
    .map((row) => {
      const cells = row.split(',');
      return {
        id: cells[idx.id].trim(),
        lat: Number(cells[idx.lat]),
        lon: Number(cells[idx.lon]),
        demand: Number(cells[idx.demand]),
      };
    });
  // Routes, tooltips and the result tables all key on node_id.
  const seen = new Set<string>();
  for (const node of nodes) {
    if (seen.has(node.id)) throw new Error(`CSV has a duplicate node_id: ${node.id}`);
    seen.add(node.id);
    if (![node.lat, node.lon, node.demand].every(Number.isFinite)) {
      throw new Error(`CSV row for node ${node.id} has a non-numeric lat/lon/demand`);
    }
  }
  return nodes;
}

export function SetupScreen() {
  const { setup } = useAppState();
  const { startJob, updateSetup } = useAppActions();
  const { cityId, nodes, usingDefault, vehicleCapacity, numVehicles, accidentEdges } = setup;

  const [cities, setCities] = useState<City[]>([]);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [accidentMode, setAccidentMode] = useState(false);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [edgesError, setEdgesError] = useState<string | null>(null);

  useEffect(() => {
    fetchCities()
      .then((list) => {
        setCities(list);
        // Keep the city the user already picked when coming Back to Setup.
        if (list.length > 0 && !list.some((c) => c.id === cityId)) updateSetup({ cityId: list[0].id });
      })
      .catch(() => setCsvError('Could not reach backend for the city list.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Real road network is always visible as map context (not just during
  // accident picking) -- fetch it as soon as a city is known.
  useEffect(() => {
    if (!cityId) return;
    fetchEdges(cityId)
      .then(setEdges)
      .catch(() => setEdgesError('Could not load road segments for this city.'));
  }, [cityId]);

  function handleEdgeClick(edge: GraphEdge) {
    const already = accidentEdges.some(
      (a) => edgeIdFor(a.fromNodeId, a.toNodeId) === edge.edgeId,
    );
    if (already) return;
    updateSetup({ accidentEdges: [...accidentEdges, { fromNodeId: edge.fromNodeId, toNodeId: edge.toNodeId }] });
  }

  const canRun = cityId !== '' && nodes.length >= 2 && !submitting;

  const MAX_CSV_BYTES = 5 * 1024 * 1024; // PRD Section 17

  async function handleFile(file: File) {
    setCsvError(null);
    if (file.size > MAX_CSV_BYTES) {
      updateSetup({ nodes: [] });
      setCsvError('CSV exceeds 5 MB limit.');
      return;
    }
    try {
      const text = await file.text();
      updateSetup({ nodes: parseNodesCsv(text), usingDefault: false });
    } catch (err) {
      updateSetup({ nodes: [] });
      setCsvError(err instanceof Error ? err.message : 'Could not parse CSV.');
    }
  }

  async function handleRun() {
    setSubmitting(true);
    setSubmitError(null);
    const scenario = {
      cityId,
      nodes,
      vehicleCapacity,
      numVehicles,
      seed: 42,
      timeBudgetS: 8.0,
      accidentEdges,
    };
    try {
      const jobId = await createJob(scenario);
      startJob(scenario, jobId);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Could not start the job.');
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: '100svh' }}>
      <div
        style={{
          width: '30%', minWidth: 320, height: '100vh', overflowY: 'auto',
          display: 'flex', flexDirection: 'column',
          borderRight: '1px solid var(--border-subtle)',
        }}
      >
      <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', flex: 1 }}>
        <h1 className="text-display">City / Network Setup</h1>

        <label className="text-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          City
          <select
            value={cityId}
            onChange={(e) => updateSetup({ cityId: e.target.value })}
            style={selectStyle}
          >
            {cities.length === 0 && <option value="">Loading…</option>}
            {cities.map((city) => (
              <option key={city.id} value={city.id}>{city.name}</option>
            ))}
          </select>
        </label>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <span className="text-body">Delivery nodes (CSV)</span>
          <input
            type="file"
            accept=".csv"
            aria-label="Upload delivery-node CSV"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <a
            className="text-caption"
            href={`data:text/csv;charset=utf-8,${encodeURIComponent(CSV_TEMPLATE)}`}
            download="node_template.csv"
            style={{ color: 'var(--text-primary)', textDecoration: 'underline' }}
          >
            Download CSV template
          </a>
          {csvError && <span className="text-caption" style={{ color: 'var(--status-error)' }}>{csvError}</span>}
          {nodes.length > 0 && !csvError && (
            <span className="text-caption">
              {usingDefault
                ? `Using default 5-node demo scenario (depot: ${nodes[0]?.id})`
                : `${nodes.length} nodes loaded (depot: ${nodes[0]?.id})`}
            </span>
          )}
          <NodeTable nodes={nodes} />
        </div>

        <label className="text-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          Vehicle capacity
          <input
            type="number" min={1} value={vehicleCapacity}
            onChange={(e) => updateSetup({ vehicleCapacity: Number(e.target.value) })}
            style={selectStyle}
          />
        </label>

        <label className="text-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          Number of vehicles
          <input
            type="number" min={1} value={numVehicles}
            onChange={(e) => updateSetup({ numVehicles: Number(e.target.value) })}
            style={selectStyle}
          />
        </label>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <button
            onClick={() => setAccidentMode((prev) => !prev)}
            style={{
              ...toggleButtonStyle,
              borderColor: accidentMode ? 'var(--status-error)' : 'var(--border-subtle)',
              color: accidentMode ? 'var(--status-error)' : 'var(--text-secondary)',
            }}
          >
            {accidentMode ? 'Click road segments on the map → (click here when done)' : 'Inject Accidents'}
          </button>
          {edgesError && <span className="text-caption" style={{ color: 'var(--status-error)' }}>{edgesError}</span>}
          {accidentEdges.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }} data-testid="accident-list">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-caption">{accidentEdges.length} active accident{accidentEdges.length > 1 ? 's' : ''}</span>
                <button
                  onClick={() => updateSetup({ accidentEdges: [] })}
                  className="text-caption"
                  style={linkButtonStyle}
                >
                  Clear all
                </button>
              </div>
              {accidentEdges.map((a, i) => {
                const id = edgeIdFor(a.fromNodeId, a.toNodeId);
                return (
                  <div key={id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span
                      className="text-caption"
                      style={{
                        background: 'var(--status-error)', color: 'var(--bg-canvas)',
                        borderRadius: 'var(--radius-sm)', padding: '2px 8px', fontWeight: 600,
                      }}
                    >
                      ×5 delay
                    </span>
                    <span className="text-caption" style={{ flex: 1 }}>Accident {i + 1} · road {id}</span>
                    <button
                      onClick={() =>
                        updateSetup({ accidentEdges: accidentEdges.filter((_, j) => j !== i) })
                      }
                      aria-label={`Remove accident ${i + 1}`}
                      className="text-caption"
                      style={linkButtonStyle}
                    >
                      Remove
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {submitError && <span className="text-caption" style={{ color: 'var(--status-error)' }}>{submitError}</span>}
      </div>

      <div
        style={{
          position: 'sticky', bottom: 0, background: 'var(--bg-canvas)',
          borderTop: '1px solid var(--border-subtle)', padding: 'var(--space-4) var(--space-6)',
        }}
      >
        <button
          onClick={handleRun}
          disabled={!canRun}
          style={{
            width: '100%', padding: 'var(--space-4)',
            background: canRun ? 'var(--text-primary)' : 'var(--bg-surface-raised)',
            color: canRun ? 'var(--bg-canvas)' : 'var(--text-secondary)',
            border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 600,
          }}
        >
          {submitting ? 'Starting…' : 'Run Optimization'}
        </button>
      </div>
      </div>

      <div style={{ width: '70%', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <MapLegend showAccidents={accidentEdges.length > 0 || accidentMode} />
        <MapCanvas
          nodes={nodes}
          heightPx={560}
          edges={edges}
          selectedEdgeIds={accidentEdges.map((a) => edgeIdFor(a.fromNodeId, a.toNodeId))}
          onEdgeClick={accidentMode ? handleEdgeClick : undefined}
        />
        <span className="text-caption" style={{ color: 'var(--text-secondary)' }}>
          Hover a node for its id, demand and location.
        </span>
      </div>
    </div>
  );
}

const selectStyle = {
  background: 'var(--bg-surface)', color: 'var(--text-primary)',
  border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2)', fontFamily: 'var(--font-ui)',
};

const toggleButtonStyle = {
  background: 'var(--bg-surface)', color: 'var(--text-secondary)',
  border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2)',
};

const linkButtonStyle = {
  background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline',
};
