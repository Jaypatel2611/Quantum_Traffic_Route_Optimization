interface InfoIconProps {
  size?: number;
}

/** Drawn SVG, not a Unicode glyph -- floor's icon rule: icons are drawn, in
 * one consistent stroke and weight, never a Unicode/emoji stand-in. */
export function InfoIcon({ size = 14 }: InfoIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
      <line x1="8" y1="7.2" x2="8" y2="11.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="8" cy="4.8" r="0.9" fill="currentColor" />
    </svg>
  );
}
