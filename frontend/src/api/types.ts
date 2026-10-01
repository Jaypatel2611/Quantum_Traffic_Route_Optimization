export interface City {
  id: string;
  name: string;
}

export interface ScenarioNode {
  id: string;
  lat: number;
  lon: number;
  demand: number;
}

/** One visit in a route: the leg that reached it and the running totals. */
export interface Stop {
  node_id: string;
  leg_distance_m: number;
  leg_time_s: number;
  cumulative_distance_m: number;
  cumulative_time_s: number;
}

export interface Route {
  vehicle_id: string;
  node_sequence: string[];
  total_distance_m: number;
  total_time_s: number;
  /** One per node_sequence entry, same order. */
  stops?: Stop[];
  /** Legs whose road path differs from the no-accident path -- the detours accidents forced. */
  rerouted_geometry?: [number, number][][];
  /** Road-following [lat, lon] polyline; absent for raw-matrix jobs. */
  geometry?: [number, number][];
}

/** What one accident did to one solver's routes (base road time, not the random delay). */
export interface AccidentImpact {
  from_node_id: number;
  to_node_id: number;
  status: 'not_on_route' | 'rerouted' | 'driven_through';
  added_time_s: number;
}

export interface AlgorithmResult {
  routes: Route[];
  accident_impacts?: AccidentImpact[];
  meta: Record<string, unknown>;
  total_co2_kg: number;
  total_time_s: number;
}

export interface GreenImpact {
  co2_saved_kg: number;
  co2_reduction_percent: number;
  fuel_saved_liters: number;
  time_saved_s: number;
  emission_factor_source: string;
}

export interface AccidentEdge {
  fromNodeId: number;
  toNodeId: number;
}

export interface JobResultDone {
  status: 'done';
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
  green_impact: GreenImpact;
  accident_edges: { from_node_id: number; to_node_id: number }[];
}

export interface JobResultPending {
  status: 'running' | 'error';
  detail?: string;
}

export type JobResult = JobResultDone | JobResultPending;

/** One undirected road segment from GET /cities/{city_id}/edges -- Flow C's
 * accident-injection map renders and picks from these. */
export interface GraphEdge {
  edgeId: string;
  fromNodeId: number;
  toNodeId: number;
  fromLat: number;
  fromLon: number;
  toLat: number;
  toLon: number;
}

export interface ScenarioConfig {
  cityId: string;
  nodes: ScenarioNode[];
  vehicleCapacity: number;
  numVehicles: number;
  seed: number;
  timeBudgetS: number;
  accidentEdges: AccidentEdge[];
}

/** Setup-screen form state, kept in AppState so going Back from Live Run /
 * Results restores the uploaded CSV, accidents and settings untouched. */
export interface SetupDraft {
  cityId: string;
  nodes: ScenarioNode[];
  usingDefault: boolean;
  vehicleCapacity: number;
  numVehicles: number;
  accidentEdges: AccidentEdge[];
}
