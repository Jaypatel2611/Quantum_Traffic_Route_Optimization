import type { ScenarioNode } from '../api/types';

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
