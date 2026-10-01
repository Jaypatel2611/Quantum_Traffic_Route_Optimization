import { describe, it, expect } from 'vitest';
import { edgeIdFor, parseNodesCsv } from './SetupScreen';

describe('parseNodesCsv', () => {
  it('parses node_id/lat/lon/demand rows, first row is the depot', () => {
    const csv = 'node_id,lat,lon,demand\ndepot,12.9716,77.6412,0\nn1,12.9750,77.6440,30\n';
    const nodes = parseNodesCsv(csv);
    expect(nodes).toEqual([
      { id: 'depot', lat: 12.9716, lon: 77.6412, demand: 0 },
      { id: 'n1', lat: 12.975, lon: 77.644, demand: 30 },
    ]);
  });

  it('throws when a required column is missing', () => {
    expect(() => parseNodesCsv('node_id,lat,lon\ndepot,12.9,77.6\n')).toThrow(/must have columns/i);
  });

  it('rejects a duplicate node_id (routes and tables key on it)', () => {
    const csv = ['node_id,lat,lon,demand', 'depot,12.9,77.6,0', 'n1,12.91,77.61,5', 'n1,12.92,77.62,6'].join('\n');
    expect(() => parseNodesCsv(csv)).toThrow(/duplicate node_id: n1/i);
  });

  it('rejects a non-numeric lat/lon/demand cell', () => {
    const csv = ['node_id,lat,lon,demand', 'depot,12.9,77.6,0', 'n1,abc,77.61,5'].join('\n');
    expect(() => parseNodesCsv(csv)).toThrow(/non-numeric/i);
  });

  it('keeps every CSV row with its own demand, in file order', () => {
    const csv = ['node_id,lat,lon,demand', 'depot,12.9,77.6,0', 'z9,12.91,77.61,7', 'a1,12.92,77.62,3'].join('\n');
    expect(parseNodesCsv(csv).map((n) => [n.id, n.demand])).toEqual([['depot', 0], ['z9', 7], ['a1', 3]]);
  });

  it('ignores trailing blank lines', () => {
    const csv = 'node_id,lat,lon,demand\ndepot,12.9716,77.6412,0\n\n';
    expect(parseNodesCsv(csv)).toHaveLength(1);
  });
});

describe('edgeIdFor', () => {
  it('matches the backend\'s min/max convention regardless of argument order', () => {
    expect(edgeIdFor(5, 3)).toBe('3_5');
    expect(edgeIdFor(3, 5)).toBe('3_5');
  });
});
