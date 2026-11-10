import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMonthly, useOverview } from "../../api/queries";
import type { SectionSpend, TopItem } from "../../api/types";
import { SpendBarChart } from "../../components/charts/SpendBarChart";
import { FilterBar, useRangeLabel } from "../../components/filters/FilterBar";
import { ProductThumb, itemPath } from "../../components/ProductThumb";
import { Card, Delta, EmptyState, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";
import { useFilters } from "../../lib/filters";
import { isoDate, monthPeriod, singleMonth } from "../../lib/period";

function RankList({ items, metric }: { items: TopItem[]; metric: "spent" | "purchases" }) {
  const { t } = useTranslation();
  const f = useFormatters();
  const max = Math.max(...items.map((i) => Number(i[metric])), 1);
  if (!items.length) return <EmptyState>{t("spending.noItems")}</EmptyState>;
  return (
    <ol className="rank">
      {items.map((item) => (
        <li key={item.key}>
          <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <ProductThumb src={item.thumbnail} />
            <Link to={itemPath(item)}>{item.name}</Link>
          </span>
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

function contextStart(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return isoDate(new Date(y, m - 12, 1));
}

export const sectionKey = (s: { id: number | null }) => (s.id === null ? "none" : String(s.id));

function SectionList({
  sections,
  selected,
  onSelect,
}: {
  sections: SectionSpend[];
  selected: string[];
  onSelect: (key: string) => void;
}) {
  const { t } = useTranslation();
  const f = useFormatters();
  if (!sections.length) return <EmptyState>{t("spending.noItems")}</EmptyState>;
  const max = Number(sections[0].spent) || 1;
  return (
    <ol className="rank">
      {sections.map((s) => {
        const key = sectionKey(s);
        return (
          <li key={key}>
            <button
              className="link-button"
              aria-pressed={selected.length === 1 && selected[0] === key}
              onClick={() => onSelect(key)}
              title={t("spending.filterBySection")}
            >
              {s.section ?? t("filters.uncategorised")}
            </button>
            <span className="num secondary">
              {f.currency(s.spent)} · {f.percent(s.share, false)}
            </span>
            <span className="bar">
              <span
                style={{
                  width: `${(Number(s.spent) / max) * 100}%`,
                  background: s.id === null ? "var(--muted)" : undefined,
                }}
              />
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function SpendingPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const rangeLabel = useRangeLabel();
  const filters = useFilters();
  const month = singleMonth(filters.range);
  // A single month is shown in context: the 12 months up to it, with it highlighted
  const monthly = useMonthly(
    month ? { ...filters.query, from: contextStart(month), to: filters.range.to } : filters.query,
  );
  const overview = useOverview(filters.query);

  const o = overview.data;
  const rows = monthly.data ?? [];
  const previous = o?.previous ? Number(o.previous.total) : 0;
  const change = o && previous ? ((Number(o.total) - previous) / previous) * 100 : null;
  const { from, to } = filters.range;
  const receiptsLink = `/receipts?${new URLSearchParams({
    ...(from ? { date_from: from } : {}),
    ...(to ? { date_to: to } : {}),
  })}`;

  return (
    <div className="page">
      <PageHeader
        title={t("spending.title")}
        subtitle={t("spending.subtitle")}
        actions={
          <Link className="btn" to="/compare">
            {t("spending.compare")}
          </Link>
        }
      />
      <FilterBar filters={filters} />
      {filters.sections.length > 0 && <p className="muted" style={{ margin: 0, fontSize: 13 }}>{t("spending.sectionsNote")}</p>}

      {overview.isError && <ErrorState onRetry={() => overview.refetch()} />}

      <div className="grid grid-4">
        {o ? (
          <>
            <StatTile
              label={t("spending.periodTotal")}
              value={f.currency(o.total)}
              foot={
                o.previous && (
                  <>
                    {change !== null && <Delta value={change} label={f.percent(change)} />}
                    <span>
                      {t("spending.vsPrevious", {
                        total: f.currency(o.previous.total),
                        range: rangeLabel({ from: o.previous.from ?? undefined, to: o.previous.to ?? undefined }),
                      })}
                    </span>
                  </>
                )
              }
            />
            <StatTile
              label={t("spending.receipts")}
              value={o.receipts}
              foot={<Link to={receiptsLink}>{t("spending.seeReceipts")}</Link>}
            />
            <StatTile
              label={t("spending.averageMonth")}
              value={f.currency(o.average_month)}
              foot={t("spending.monthsCount", { count: o.months })}
            />
            <StatTile label={t("spending.averageReceipt")} value={f.currency(o.average_receipt)} />
          </>
        ) : (
          Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="card">
              <Loading rows={2} />
            </div>
          ))
        )}
      </div>

      <Card
        title={t("spending.chartTitle")}
        subtitle={month ? f.monthLong(month) : rangeLabel(filters.range)}
      >
        {monthly.data ? (
          <SpendBarChart
            ariaLabel={t("spending.chartTitle")}
            height={300}
            selected={month ?? undefined}
            onSelect={(m) => filters.setPeriod(monthPeriod(m))}
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

      <div className="grid grid-2">
        <Card title={t("spending.topBySpend")}>
          {o ? <RankList items={o.by_spend} metric="spent" /> : <Loading rows={6} />}
        </Card>
        <Card title={t("spending.topByPurchases")}>
          {o ? <RankList items={o.by_purchases} metric="purchases" /> : <Loading rows={6} />}
        </Card>
      </div>

      <Card
        title={t("spending.categoriesTitle")}
        subtitle={t("spending.categoriesSubtitle")}
        actions={
          filters.sections.length > 0 && (
            <Link to={`/products?sections=${filters.sections.join(",")}`}>{t("spending.seeProducts")}</Link>
          )
        }
      >
        {o ? (
          <SectionList
            sections={o.sections}
            selected={filters.sections}
            onSelect={(key) =>
              filters.setSections(filters.sections.length === 1 && filters.sections[0] === key ? [] : [key])
            }
          />
        ) : (
          <Loading rows={6} />
        )}
      </Card>

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
                <tr
                  key={m.month}
                  className="clickable"
                  aria-selected={m.month === month}
                  onClick={() => filters.setPeriod(monthPeriod(m.month))}
                >
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
                <td className="right num">{f.currency(rows.reduce((s, m) => s + Number(m.total), 0))}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
