import { hslToRgb } from './nodeColor';

export type Solver = 'ortools' | 'qpso';

// Each solver keeps its reserved hue (DESIGN.md's One Meaning Rule: blue =
// OR-Tools, amber = QPSO); vehicles within a solver differ by lightness, and
// the first vehicle is exactly the solver's base color.
const BASE: Record<Solver, [number, number, number]> = {
  ortools: [46, 107, 230],
  qpso: [232, 135, 30],
};
const HUE: Record<Solver, number> = { ortools: 221, qpso: 30 };
const LIGHTNESS = [0.72, 0.36, 0.82, 0.62, 0.28];

export function vehicleColor(solver: Solver, index: number): [number, number, number] {
  if (index === 0) return BASE[solver];
  return hslToRgb(HUE[solver], 0.75, LIGHTNESS[(index - 1) % LIGHTNESS.length]);
}

/** Selection key for one solver's vehicle, e.g. "qpso:v1". */
export function routeKey(solver: Solver, vehicleId: string): string {
  return `${solver}:${vehicleId}`;
}
