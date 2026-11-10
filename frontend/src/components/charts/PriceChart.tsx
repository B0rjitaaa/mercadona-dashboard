import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFormatters } from "../../i18n/format";
import { useCssVars } from "../../lib/theme";
import { niceTicks } from "../../lib/ticks";
import { ChartTooltip } from "./ChartTooltip";

export interface PricePoint {
  t: number; // epoch ms
  price: number;
}

/** Paid unit price at each purchase. */
export function PriceChart({
  data,
  unitSuffix = "",
  height = 260,
  ariaLabel,
}: {
  data: PricePoint[];
  unitSuffix?: string;
  height?: number;
  ariaLabel: string;
}) {
  const f = useFormatters();
  const c = useCssVars(["series-1", "grid", "axis", "muted", "surface"] as const);
  const prices = data.map((d) => d.price);
  const ticks = niceTicks(Math.min(...prices), Math.max(...prices)).filter((v) => v >= 0);

  return (
    <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid vertical={false} stroke={c.grid} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(t: number) => f.monthShort(new Date(t).toISOString().slice(0, 7))}
            tickLine={false}
            axisLine={{ stroke: c.axis }}
            tick={{ fill: c.muted, fontSize: 12 }}
            minTickGap={32}
          />
          <YAxis
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            tickFormatter={(v: number) => f.currency(v)}
            tickLine={false}
            axisLine={false}
            tick={{ fill: c.muted, fontSize: 12 }}
            width={72}
          />
          <Tooltip
            cursor={{ stroke: c.axis }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <ChartTooltip
                  title={f.date(new Date(payload[0].payload.t))}
                  value={`${f.currency(payload[0].payload.price)}${unitSuffix}`}
                />
              ) : null
            }
          />
          <Line
            type="stepAfter"
            dataKey="price"
            stroke={c["series-1"]}
            strokeWidth={2}
            dot={data.length <= 40 ? { r: 4, fill: c["series-1"], stroke: c.surface, strokeWidth: 2 } : false}
            activeDot={{ r: 5, fill: c["series-1"], stroke: c.surface, strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
