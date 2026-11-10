import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMonthly, useTopItems } from "../../api/queries";
import type { TopItem } from "../../api/types";
import { SpendBarChart } from "../../components/charts/SpendBarChart";
import { Card, EmptyState, Loading, PageHeader, StatTile } from "../../components/ui";
import { currentMonthKey, monthRange, useFormatters } from "../../i18n/format";

const RANGES = ["6", "12", "24", "all"] as const;

function RankList({ items, metric }: { items: TopItem[]; metric: "spent" | "purchases" }) {
  const { t } = useTranslation();
  const f = useFormatters();
  const max = Math.max(...items.map((i) => Number(i[metric])), 1);
  if (!items.length) return <EmptyState>{t("spending.noItems")}</EmptyState>;
  return (
    <ol className="rank">
      {items.map((item) => (
        <li key={item.description}>
          <Link to={`/products/${encodeURIComponent(item.description)}`}>{item.description}</Link>
          <span className="num secondary">
            {metric === "spent" ? f.currency(item.spent) : t("spending.times", { count: item.purchases })}
          </span>
          <span className="bar">
            <span style={{ width: `${(Number(item[metric]) / max) * 100}%` }} />
          </span>
        </li>
      ))}
    </ol>
  );
}

export function SpendingPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const [params, setParams] = useSearchParams();
  const range = params.get("range") ?? "12";
  const month = params.get("month") ?? currentMonthKey();
  const monthly = useMonthly(range);
  const top = useTopItems(month);

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    setParams(next, { replace: true });
  };

  const rows = monthly.data ?? [];
  const selected = rows.find((m) => m.month === month);
  const active = rows.filter((m) => m.receipts > 0);
  const rangeTotal = rows.reduce((sum, m) => sum + Number(m.total), 0);
  const { from, to } = monthRange(month);

  return (
    <div className="page">
      <PageHeader
        title={t("spending.title")}
        subtitle={t("spending.subtitle")}
        actions={
          <div className="segmented" role="group" aria-label={t("spending.range")}>
            {RANGES.map((r) => (
              <button key={r} aria-pressed={range === r} onClick={() => set("range", r)}>
                {t(`spending.ranges.${r}`)}
              </button>
            ))}
          </div>
        }
      />

      <Card
        title={t("spending.chartTitle")}
        subtitle={
          monthly.data
            ? t("spending.chartSubtitle", {
                total: f.currency(rangeTotal),
                average: f.currency(active.length ? rangeTotal / active.length : 0),
              })
            : undefined
        }
      >
        {monthly.data ? (
          <SpendBarChart
            ariaLabel={t("spending.chartTitle")}
            height={300}
            selected={month}
            onSelect={(m) => set("month", m)}
            data={rows.map((m) => ({
              key: m.month,
              value: Number(m.total),
              extra: t("dashboard.receiptsCount", { count: m.receipts }),
            }))}
          />
        ) : (
          <Loading rows={7} />
        )}
        <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>{t("spending.clickHint")}</p>
      </Card>

      <h2 style={{ fontSize: 18 }}>{f.monthLong(month)}</h2>
      <div className="grid grid-4">
        <StatTile label={t("spending.monthTotal")} value={f.currency(selected?.total ?? 0)} />
        <StatTile label={t("spending.receipts")} value={selected?.receipts ?? 0} />
        <StatTile label={t("spending.averageReceipt")} value={f.currency(selected?.average_receipt ?? 0)} />
        <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Link className="btn" to={`/receipts?date_from=${from}&date_to=${to}`}>
            {t("spending.seeReceipts")}
          </Link>
        </div>
      </div>

      <div className="grid grid-2">
        <Card title={t("spending.topBySpend")}>
          {top.data ? <RankList items={top.data.by_spend} metric="spent" /> : <Loading rows={6} />}
        </Card>
        <Card title={t("spending.topByPurchases")}>
          {top.data ? <RankList items={top.data.by_purchases} metric="purchases" /> : <Loading rows={6} />}
        </Card>
      </div>

      <Card title={t("spending.tableTitle")}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("spending.month")}</th>
                <th className="right">{t("spending.receipts")}</th>
                <th className="right">{t("spending.averageReceipt")}</th>
                <th className="right">{t("spending.monthTotal")}</th>
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map((m) => (
                <tr key={m.month} className="clickable" onClick={() => set("month", m.month)}>
                  <td>{f.monthLong(m.month)}</td>
                  <td className="right num">{m.receipts}</td>
                  <td className="right num">{f.currency(m.average_receipt)}</td>
                  <td className="right num">{f.currency(m.total)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>{t("spending.total")}</td>
                <td className="right num">{rows.reduce((s, m) => s + m.receipts, 0)}</td>
                <td />
                <td className="right num">{f.currency(rangeTotal)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
