import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useTranslation } from "react-i18next";
import { useFormatters } from "../../i18n/format";
import { useCssVars } from "../../lib/theme";
import { niceTicks } from "../../lib/ticks";

export interface PricePoint {
  t: number; // epoch ms
  price: number;
}

interface Row {
  t: number;
  paid?: number;
  catalog?: number;
}

/** Paid unit price at each purchase, plus the catalogue price line when known. */
export function PriceChart({
  paid,
  catalog = [],
  unitSuffix = "",
  height = 260,
  ariaLabel,
}: {
  paid: PricePoint[];
  catalog?: PricePoint[];
  unitSuffix?: string;
  height?: number;
  ariaLabel: string;
}) {
  const { t } = useTranslation();
  const f = useFormatters();
  const c = useCssVars(["series-1", "series-2", "grid", "axis", "muted", "surface"] as const);

  // The catalogue price holds until the next change: extend its last value to today.
  const catalogLine = [...catalog];
  if (catalogLine.length) {
    const end = Math.max(Date.now(), ...paid.map((p) => p.t));
    catalogLine.push({ t: end, price: catalogLine[catalogLine.length - 1].price });
  }
  const byTime = new Map<number, Row>();
  for (const p of paid) byTime.set(p.t, { ...byTime.get(p.t), t: p.t, paid: p.price });
  for (const p of catalogLine) byTime.set(p.t, { ...byTime.get(p.t), t: p.t, catalog: p.price });
  const data = [...byTime.values()].sort((a, b) => a.t - b.t);

  const values = [...paid, ...catalogLine].map((p) => p.price);
  const ticks = niceTicks(Math.min(...values), Math.max(...values)).filter((v) => v >= 0);
  const showDots = paid.length <= 40;

  return (
    <div>
      {catalog.length > 0 && (
        <div className="legend" style={{ marginBottom: 8 }}>
          <span>
            <i style={{ background: c["series-1"] }} />
            {t("product.paidSeries")}
          </span>
          <span>
            <i style={{ background: c["series-2"] }} />
            {t("product.catalogSeries")}
          </span>
        </div>
      )}
      <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
            <CartesianGrid vertical={false} stroke={c.grid} />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v: number) => f.monthShort(new Date(v).toISOString().slice(0, 7))}
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
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const row = payload[0].payload as Row;
                return (
                  <div className="chart-tooltip">
                    <div className="t-title">{f.date(new Date(row.t))}</div>
                    {row.paid !== undefined && (
                      <div className="num">
                        {t("product.paidSeries")}: <strong>{f.currency(row.paid)}{unitSuffix}</strong>
                      </div>
                    )}
                    {row.catalog !== undefined && (
                      <div className="num">
                        {t("product.catalogSeries")}: <strong>{f.currency(row.catalog)}{unitSuffix}</strong>
                      </div>
                    )}
                  </div>
                );
              }}
            />
            <Line
              type="stepAfter"
              dataKey="paid"
              connectNulls
              stroke={c["series-1"]}
              strokeWidth={2}
              dot={showDots ? { r: 4, fill: c["series-1"], stroke: c.surface, strokeWidth: 2 } : false}
              activeDot={{ r: 5, fill: c["series-1"], stroke: c.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
            {catalog.length > 0 && (
              <Line
                type="stepAfter"
                dataKey="catalog"
                connectNulls
                stroke={c["series-2"]}
                strokeWidth={2}
                // With little catalogue history the line is too short to see: mark its points
                dot={catalog.length <= 3 ? { r: 4, fill: c["series-2"], stroke: c.surface, strokeWidth: 2 } : false}
                activeDot={{ r: 5, fill: c["series-2"], stroke: c.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
