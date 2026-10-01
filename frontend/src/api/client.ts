import type { City, GraphEdge, JobResult, ScenarioConfig } from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchCities(): Promise<City[]> {
  return getJson<City[]>('/cities');
}

interface EdgeWire {
  edge_id: string;
  from_node_id: number;
  to_node_id: number;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
}

export async function fetchEdges(cityId: string): Promise<GraphEdge[]> {
  const wire = await getJson<EdgeWire[]>(`/cities/${cityId}/edges`);
  return wire.map((e) => ({
    edgeId: e.edge_id,
    fromNodeId: e.from_node_id,
    toNodeId: e.to_node_id,
    fromLat: e.from_lat,
    fromLon: e.from_lon,
    toLat: e.to_lat,
    toLon: e.to_lon,
  }));
}

export async function createJob(scenario: ScenarioConfig): Promise<string> {
  const response = await fetch(`${BASE_URL}/jobs/from-nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      city_id: scenario.cityId,
      nodes: scenario.nodes,
      vehicle_capacity: scenario.vehicleCapacity,
      num_vehicles: scenario.numVehicles,
      seed: scenario.seed,
      time_budget_s: scenario.timeBudgetS,
      accident_edges: scenario.accidentEdges.map((a) => ({
        from_node_id: a.fromNodeId,
        to_node_id: a.toNodeId,
      })),
    }),
  });
  if (!response.ok) {
    throw new Error(`job creation failed: ${response.status}`);
  }
  const data = (await response.json()) as { job_id: string };
  return data.job_id;
}

export function fetchJobResult(jobId: string): Promise<JobResult> {
  return getJson<JobResult>(`/jobs/${jobId}/result`);
}

export interface ConvergenceStreamHandlers {
  onProgress: (gbest: number) => void;
  onComplete: () => void;
  onError: (message: string) => void;
}

/** Wraps the backend's SSE stream (event: progress | complete | error) in a
 * native EventSource -- reconnect/replay is the backend's job (Section 15);
 * this just routes each named event to its handler and closes the
 * connection on a terminal event so the browser doesn't keep retrying a
 * finished job. */
export function subscribeToConvergence(jobId: string, handlers: ConvergenceStreamHandlers): () => void {
  const source = new EventSource(`${BASE_URL}/jobs/${jobId}/stream`);

  source.addEventListener('progress', (event) => {
    const data = JSON.parse((event as MessageEvent).data) as { gbest: number };
    handlers.onProgress(data.gbest);
  });
  source.addEventListener('complete', () => {
    handlers.onComplete();
    source.close();
  });
  source.addEventListener('error', (event) => {
    const messageEvent = event as MessageEvent;
    if (messageEvent.data) {
      // The backend's named `event: error` -- the solver itself failed.
      // Always terminal.
      const detail = (JSON.parse(messageEvent.data) as { detail?: string }).detail;
      handlers.onError(detail ?? 'unknown solver error');
      source.close();
      return;
    }
    // A plain connection-level error. EventSource retries on its own unless
    // it has already given up (readyState CLOSED) -- only report/stop then,
    // so a transient network blip doesn't kill a recoverable stream
    // (PRD Section 15's reconnect-and-replay guarantee).
    if (source.readyState === EventSource.CLOSED) {
      handlers.onError('connection lost');
    }
  });

  return () => source.close();
}
