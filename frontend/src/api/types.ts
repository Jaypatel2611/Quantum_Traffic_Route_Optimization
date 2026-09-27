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

export interface Route {
  vehicle_id: string;
  node_sequence: string[];
  total_distance_m: number;
  total_time_s: number;
}

export interface AlgorithmResult {
  routes: Route[];
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

export interface JobResultDone {
  status: 'done';
  ortools: AlgorithmResult;
  qpso: AlgorithmResult;
  green_impact: GreenImpact;
}

export interface JobResultPending {
  status: 'running' | 'error';
  detail?: string;
}

export type JobResult = JobResultDone | JobResultPending;

export interface AccidentEdge {
  fromNodeId: string;
  toNodeId: string;
}

export interface ScenarioConfig {
  cityId: string;
  nodes: ScenarioNode[];
  vehicleCapacity: number;
  numVehicles: number;
  seed: number;
  timeBudgetS: number;
  accidentEdge: AccidentEdge | null;
}
