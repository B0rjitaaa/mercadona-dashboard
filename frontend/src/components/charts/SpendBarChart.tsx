import { Bar, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFormatters } from "../../i18n/format";
import { useCssVars } from "../../lib/theme";
import { niceTicks } from "../../lib/ticks";
import { ChartTooltip } from "./ChartTooltip";

export interface SpendBar {
  key: string; // YYYY-MM unless the chart is given its own formatters
  value: number;
  extra?: string;
  /** Optional second measure in the same unit (euros), drawn as a line over the columns */
  line?: number;
}

/** Column chart of spend per month (or per any bucket with `formatTick` and `formatTitle`),
 * optionally with a line in the same unit on the same axis. Click a column to select it. */
export function SpendBarChart({
  data,
  selected,
  onSelect,
  height = 260,
  ariaLabel,
  formatTick,
  formatTitle,
  barLabel,
  lineLabel,
}: {
  data: SpendBar[];
  selected?: string;
  onSelect?: (key: string) => void;
  height?: number;
  ariaLabel: string;
  formatTick?: (key: string) => string;
  formatTitle?: (key: string) => string;
  /** Legend names; the legend is shown only when the line is */
  barLabel?: string;
  lineLabel?: string;
}) {
  const f = useFormatters();
  const c = useCssVars(["series-1", "series-1-muted", "series-2", "surface", "grid", "axis", "muted", "surface-2"] as const);
  const dense = data.length > 18;
  const hasLine = Boolean(lineLabel) && data.some((d) => d.line !== undefined);
  const ticks = niceTicks(0, Math.max(...data.map((d) => Math.max(d.value, d.line ?? 0)), 0));

  return (
    <div>
      {hasLine && (
        <div className="legend" style={{ marginBottom: 8 }}>
          <span>
            <i className="dot" style={{ background: c["series-1"], borderRadius: 2 }} />
            {barLabel}
          </span>
          <span>
            <i style={{ background: c["series-2"] }} />
            {lineLabel}
          </span>
        </div>
      )}
      <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 4 }} barCategoryGap={dense ? 2 : "20%"}>
            <CartesianGrid vertical={false} stroke={c.grid} />
            <XAxis
              dataKey="key"
              tickFormatter={formatTick ?? f.monthShort}
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
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as SpendBar;
                return (
                  <ChartTooltip
                    title={(formatTitle ?? f.monthLong)(d.key)}
                    value={f.currency(d.value)}
                    extra={
                      <>
                        {d.extra}
                        {hasLine && d.line !== undefined && (
                          <div>
                            {lineLabel}: {f.currency(d.line)}
                          </div>
                        )}
                      </>
                    }
                  />
                );
              }}
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
                <Cell key={d.key} fill={!selected || d.key === selected ? c["series-1"] : c["series-1-muted"]} />
              ))}
            </Bar>
            {hasLine && (
              <Line
                dataKey="line"
                type="monotone"
                stroke={c["series-2"]}
                strokeWidth={2}
                dot={dense ? false : { r: 4, fill: c["series-2"], stroke: c.surface, strokeWidth: 2 }}
                activeDot={{ r: 5, fill: c["series-2"], stroke: c.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
