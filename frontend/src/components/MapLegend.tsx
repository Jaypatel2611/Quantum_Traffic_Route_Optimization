import type { ReactNode } from 'react';

interface MapLegendProps {
  showAccidents?: boolean;
  showRerouted?: boolean;
}

/** What each marker on the map means, so depot / customer nodes / accident
 * roads / detours are never ambiguous. */
export function MapLegend({ showAccidents = true, showRerouted = false }: MapLegendProps) {
  return (
    <div className="text-caption" style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'center' }}>
      <Entry swatch={<Dot color="#edeff2" size={12} />} label="Depot" />
      <Entry swatch={<Dot color="#d4607a" size={9} />} label="Delivery node (color = node identity)" />
      {showAccidents && (
        <Entry
          swatch={
            <svg width="22" height="8" aria-hidden="true">
              <line x1="0" y1="4" x2="22" y2="4" stroke="#e5484d" strokeWidth="4" strokeDasharray="5 3" />
            </svg>
          }
          label="Accident road (×5 delay)"
        />
      )}
      {showRerouted && (
        <Entry
          swatch={
            <svg width="22" height="10" aria-hidden="true">
              <line x1="0" y1="5" x2="22" y2="5" stroke="#f2c94c" strokeWidth="8" strokeLinecap="round" />
            </svg>
          }
          label="Rerouted path (detour around accident)"
        />
      )}
    </div>
  );
}

function Dot({ color, size }: { color: string; size: number }) {
  return <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%', background: color }} />;
}

function Entry({ swatch, label }: { swatch: ReactNode; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      {swatch}
      {label}
    </span>
  );
}
