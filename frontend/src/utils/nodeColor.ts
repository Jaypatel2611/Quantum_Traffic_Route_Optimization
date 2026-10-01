/** Deterministic per-node identity color, shared by every screen that draws
 * nodes on a MapCanvas. Same node id -> same color everywhere (Setup,
 * Results, ...), so a specific delivery node can be visually tracked across
 * screens. Never draws from the reserved route-classical/route-quantum/
 * accent-eco hues (DESIGN.md's One Meaning Rule) -- see DESIGN.md's
 * "Node Identity Color" rule for the full rationale. */

// Hand-picked hues that stay clear of the reserved tokens: route-classical
// blue (~221deg), route-quantum amber (~30deg), accent-eco green (~152deg),
// and the brief's rejected purple/violet band (~260-300deg).
const HUES = [0, 10, 55, 70, 85, 175, 185, 305, 325, 345];
const SATURATION = 0.62;
// A second lightness step so two nodes that land on the same hue (10 hues,
// small node counts -- the 5-node demo scenario included) still read as
// visibly different dots instead of a same-hue collision.
const LIGHTNESSES = [0.48, 0.62];

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let [r, g, b] = [0, 0, 0];
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

const CACHE = new Map<string, [number, number, number]>();

export function colorForNode(id: string): [number, number, number] {
  const cached = CACHE.get(id);
  if (cached) return cached;
  const hash = hashString(id);
  const hue = HUES[hash % HUES.length];
  const lightness = LIGHTNESSES[Math.floor(hash / HUES.length) % LIGHTNESSES.length];
  const color = hslToRgb(hue, SATURATION, lightness);
  CACHE.set(id, color);
  return color;
}
