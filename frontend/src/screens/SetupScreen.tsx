import { useEffect, useState } from 'react';
import { createJob, fetchCities } from '../api/client';
import type { City, ScenarioNode } from '../api/types';
import { useAppActions } from '../state/AppState';
import { MapCanvas } from '../components/LazyMapCanvas';

const CSV_TEMPLATE = 'node_id,lat,lon,demand\ndepot,12.9716,77.6412,0\nn1,12.9750,77.6440,30\n';

/** PRD Section 16: no screen is ever actually empty in the demo. Pre-seeds
 * the same 5-node Indiranagar scenario used throughout Phase 5-7's own
 * verification (docs/demo_scenarios/indiranagar_5.csv) -- a rehearsed,
 * always-feasible starting point a judge sees immediately, not a blank
 * upload prompt. Uploading a CSV replaces it. */
const DEFAULT_SCENARIO_NODES: ScenarioNode[] = [
  { id: 'depot', lat: 12.9716, lon: 77.6412, demand: 0 },
  { id: 'n1', lat: 12.975, lon: 77.644, demand: 30 },
  { id: 'n2', lat: 12.969, lon: 77.638, demand: 40 },
  { id: 'n3', lat: 12.976, lon: 77.639, demand: 25 },
  { id: 'n4', lat: 12.967, lon: 77.643, demand: 35 },
];

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
  return rows
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
}

export function SetupScreen() {
  const { startJob } = useAppActions();
  const [cities, setCities] = useState<City[]>([]);
  const [cityId, setCityId] = useState('');
  const [nodes, setNodes] = useState<ScenarioNode[]>(DEFAULT_SCENARIO_NODES);
  const [usingDefault, setUsingDefault] = useState(true);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [vehicleCapacity, setVehicleCapacity] = useState(100);
  const [numVehicles, setNumVehicles] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    fetchCities()
      .then((list) => {
        setCities(list);
        if (list.length > 0) setCityId(list[0].id);
      })
      .catch(() => setCsvError('Could not reach backend for the city list.'));
  }, []);

  const canRun = cityId !== '' && nodes.length >= 2 && !submitting;

  async function handleFile(file: File) {
    setCsvError(null);
    try {
      const text = await file.text();
      setNodes(parseNodesCsv(text));
      setUsingDefault(false);
    } catch (err) {
      setNodes([]);
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
      accidentEdge: null,
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
            onChange={(e) => setCityId(e.target.value)}
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
        </div>

        <label className="text-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          Vehicle capacity
          <input
            type="number" min={1} value={vehicleCapacity}
            onChange={(e) => setVehicleCapacity(Number(e.target.value))}
            style={selectStyle}
          />
        </label>

        <label className="text-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          Number of vehicles
          <input
            type="number" min={1} value={numVehicles}
            onChange={(e) => setNumVehicles(Number(e.target.value))}
            style={selectStyle}
          />
        </label>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <button disabled title="Edge-level accident injection needs a graph-edge API not built in this phase" style={toggleButtonStyle}>
            Inject Accident (coming soon)
          </button>
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

      <div style={{ width: '70%', padding: 'var(--space-6)' }}>
        <MapCanvas nodes={nodes} heightPx={560} />
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
