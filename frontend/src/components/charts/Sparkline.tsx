/** Tiny trend line for table rows; last point marked. */
export function Sparkline({ values, width = 72, height = 22 }: { values: number[]; width?: number; height?: number }) {
  if (values.length < 2) return <span className="muted">—</span>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i: number) => 3 + (i / (values.length - 1)) * (width - 6);
  const y = (v: number) => (max === min ? height / 2 : 3 + (1 - (v - min) / span) * (height - 6));
  const points = values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const last = values.length - 1;
  return (
    <svg width={width} height={height} aria-hidden="true" style={{ display: "block" }}>
      <polyline points={points} fill="none" stroke="var(--series-1)" strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={x(last)} cy={y(values[last])} r={2.5} fill="var(--series-1)" />
    </svg>
  );
}
