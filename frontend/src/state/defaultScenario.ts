import type { ScenarioNode, SetupDraft } from '../api/types';

/** PRD Section 16: no screen is ever actually empty in the demo. Pre-seeds
 * the same 5-node Indiranagar scenario used throughout Phase 5-7's own
 * verification (docs/demo_scenarios/indiranagar_5.csv) -- a rehearsed,
 * always-feasible starting point a judge sees immediately, not a blank
 * upload prompt. Uploading a CSV replaces it. */
export const DEFAULT_SCENARIO_NODES: ScenarioNode[] = [
  { id: 'depot', lat: 12.9716, lon: 77.6412, demand: 0 },
  { id: 'n1', lat: 12.975, lon: 77.644, demand: 30 },
  { id: 'n2', lat: 12.969, lon: 77.638, demand: 40 },
  { id: 'n3', lat: 12.976, lon: 77.639, demand: 25 },
  { id: 'n4', lat: 12.967, lon: 77.643, demand: 35 },
];

export const INITIAL_SETUP: SetupDraft = {
  cityId: '',
  nodes: DEFAULT_SCENARIO_NODES,
  usingDefault: true,
  vehicleCapacity: 100,
  numVehicles: 2,
  accidentEdges: [],
};
