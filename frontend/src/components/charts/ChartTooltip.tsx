import type { ReactNode } from "react";

export function ChartTooltip({ title, value, extra }: { title: ReactNode; value: ReactNode; extra?: ReactNode }) {
  return (
    <div className="chart-tooltip">
      <div className="t-title">{title}</div>
      <div className="t-value num">{value}</div>
      {extra && <div className="muted num">{extra}</div>}
    </div>
  );
}
