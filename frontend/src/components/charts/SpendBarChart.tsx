import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFormatters } from "../../i18n/format";
import { useCssVars } from "../../lib/theme";
import { niceTicks } from "../../lib/ticks";
import { ChartTooltip } from "./ChartTooltip";

export interface SpendBar {
  key: string; // YYYY-MM
  value: number;
  extra?: string;
}

/** Single-series column chart of spend per month. Click a column to select it. */
export function SpendBarChart({
  data,
  selected,
  onSelect,
  height = 260,
  ariaLabel,
}: {
  data: SpendBar[];
  selected?: string;
  onSelect?: (key: string) => void;
  height?: number;
  ariaLabel: string;
}) {
  const f = useFormatters();
  const c = useCssVars(["series-1", "series-1-muted", "grid", "axis", "muted", "surface-2"] as const);
  const dense = data.length > 18;
  const ticks = niceTicks(0, Math.max(...data.map((d) => d.value), 0));

  return (
    <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 4 }} barCategoryGap={dense ? 2 : "20%"}>
          <CartesianGrid vertical={false} stroke={c.grid} />
          <XAxis
            dataKey="key"
            tickFormatter={f.monthShort}
            tickLine={false}
            axisLine={{ stroke: c.axis }}
            tick={{ fill: c.muted, fontSize: 12 }}
            interval="preserveStartEnd"
            minTickGap={dense ? 24 : 8}
          />
          <YAxis
            ticks={ticks}
            domain={[0, ticks[ticks.length - 1]]}
            tickFormatter={f.currencyAxis}
            tickLine={false}
            axisLine={false}
            tick={{ fill: c.muted, fontSize: 12 }}
            width={64}
          />
          <Tooltip
            cursor={{ fill: c["surface-2"] }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <ChartTooltip
                  title={f.monthLong(payload[0].payload.key)}
                  value={f.currency(payload[0].payload.value)}
                  extra={payload[0].payload.extra}
                />
              ) : null
            }
          />
          <Bar
            dataKey="value"
            maxBarSize={24}
            radius={[4, 4, 0, 0]}
            cursor={onSelect ? "pointer" : undefined}
            onClick={(entry: { key?: string }) => entry.key && onSelect?.(entry.key)}
            isAnimationActive={false}
          >
            {data.map((d) => (
              <Cell
                key={d.key}
                fill={!selected || d.key === selected ? c["series-1"] : c["series-1-muted"]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
