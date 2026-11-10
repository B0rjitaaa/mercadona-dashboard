import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCatalogStatus, usePriceWatch } from "../../api/queries";
import type { PriceRow } from "../../api/types";
import { ItemCell } from "../../components/ItemCell";
import { itemPath } from "../../components/ProductThumb";
import { Card, Delta, EmptyState, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

const FILTERS = ["all", "up", "down"] as const;
const WINDOWS = [7, 30, 90] as const;

function perUnit(row: PriceRow) {
  return row.catalog_per_kg ? "/kg" : "";
}

export function PricesPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [days, setDays] = useState<number>(30);
  const watch = usePriceWatch(days);
  const catalog = useCatalogStatus();
  const w = watch.data;

  if (watch.isError) return <div className="page"><ErrorState onRetry={() => watch.refetch()} /></div>;

  const alerts = (w?.alerts ?? []).filter(
    (a) => filter === "all" || (filter === "up" ? Number(a.diff) > 0 : Number(a.diff) < 0),
  );
  const impact = Number(w?.summary.impact_12m ?? 0);
  const inflation = w?.summary.inflation_12m;

  return (
    <div className="page">
      <PageHeader
        title={t("prices.title")}
        subtitle={
          w
            ? t("prices.subtitle", { count: w.regular_products, min: w.rules.min_purchases, days: w.rules.within_days })
            : undefined
        }
      />

      <div className="grid grid-4">
        {w ? (
          <>
            <StatTile label={t("prices.up")} value={w.summary.up} foot={t("prices.upFoot")} />
            <StatTile label={t("prices.down")} value={w.summary.down} foot={t("prices.downFoot")} />
            <StatTile
              label={t("prices.impact")}
              value={
                <Delta value={impact} label={`${impact > 0 ? "+" : ""}${f.currency(impact)}`} />
              }
              foot={t("prices.impactFoot")}
            />
            <StatTile
              label={t("prices.inflation")}
              value={inflation == null ? "—" : <Delta value={Number(inflation)} label={f.percent(inflation)} />}
              foot={
                inflation == null
                  ? t("prices.inflationNone")
                  : t("prices.inflationFoot", { count: w.summary.inflation_products })
              }
            />
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
        title={t("prices.alertsTitle")}
        subtitle={w ? t("prices.alertsSubtitle", { pct: f.percent(w.rules.min_pct, false) }) : undefined}
        actions={
          <div className="segmented" role="group" aria-label={t("prices.filter")}>
            {FILTERS.map((x) => (
              <button key={x} aria-pressed={filter === x} onClick={() => setFilter(x)}>
                {t(`prices.filters.${x}`)}
              </button>
            ))}
          </div>
        }
      >
        {!w && <Loading rows={6} />}
        {w && alerts.length === 0 && <EmptyState>{t("prices.noAlerts")}</EmptyState>}
        {alerts.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("products.name")}</th>
                  <th className="right">{t("prices.lastPaid")}</th>
                  <th className="right">{t("prices.now")}</th>
                  <th className="right">{t("products.change")}</th>
                  <th className="right">{t("prices.impactCol")}</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.key} className="clickable" onClick={() => navigate(itemPath(a))}>
                    <td className="wrap"><ItemCell item={a} /></td>
                    <td className="right num">
                      {f.currency(a.last_paid)}
                      {perUnit(a)}
                      <small className="muted" style={{ display: "block" }}>{f.date(a.last_paid_at)}</small>
                    </td>
                    <td className="right num">
                      {f.currency(a.catalog_price)}
                      {perUnit(a)}
                    </td>
                    <td className="right num">
                      <Delta value={Number(a.diff_pct)} label={f.percent(a.diff_pct ?? 0)} />
                    </td>
                    <td className="right num">
                      {Number(a.impact_12m) > 0 ? "+" : ""}
                      {f.currency(a.impact_12m)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {w && w.check_links.length > 0 && (
        <Card
          title={t("prices.checkTitle")}
          subtitle={t("prices.checkSubtitle", { pct: f.percent(w.rules.suspicious_pct, false) })}
        >
          <div className="table-wrap">
            <table>
              <tbody>
                {w.check_links.map((a) => (
                  <tr key={a.key}>
                    <td className="wrap"><ItemCell item={a} /></td>
                    <td className="right num secondary">
                      {t("prices.paidVsNow", { paid: f.currency(a.last_paid), now: f.currency(a.catalog_price) })}
                    </td>
                    <td className="right">
                      <Link className="btn" to={itemPath(a)}>{t("prices.checkLink")}</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Card
        title={t("prices.recentTitle")}
        subtitle={t("prices.recentSubtitle")}
        actions={
          <div className="segmented" role="group" aria-label={t("prices.window")}>
            {WINDOWS.map((d) => (
              <button key={d} aria-pressed={days === d} onClick={() => setDays(d)}>
                {t("prices.days", { count: d })}
              </button>
            ))}
          </div>
        }
      >
        {!w && <Loading rows={4} />}
        {w && w.recent_changes.length === 0 && (
          <EmptyState>
            {t("prices.noRecent", {
              date: catalog.data?.last_sync ? f.date(catalog.data.last_sync.started_at) : "—",
            })}
          </EmptyState>
        )}
        {w && w.recent_changes.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("products.name")}</th>
                  <th className="right">{t("prices.before")}</th>
                  <th className="right">{t("prices.now")}</th>
                  <th className="right">{t("products.change")}</th>
                  <th>{t("prices.changedAt")}</th>
                </tr>
              </thead>
              <tbody>
                {w.recent_changes.map((a) => (
                  <tr key={a.key} className="clickable" onClick={() => navigate(itemPath(a))}>
                    <td className="wrap">
                      <ItemCell item={a} />
                      {a.variable_weight && <span className="badge plain">{t("prices.variableWeight")}</span>}
                    </td>
                    <td className="right num secondary">
                      {f.currency(a.catalog_previous)}
                      {perUnit(a)}
                    </td>
                    <td className="right num">
                      {f.currency(a.catalog_price)}
                      {perUnit(a)}
                    </td>
                    <td className="right num">
                      <Delta value={Number(a.catalog_change_pct)} label={f.percent(a.catalog_change_pct ?? 0)} />
                    </td>
                    <td className="secondary">{f.date(a.catalog_changed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
