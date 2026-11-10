import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMonthly, usePriceWatch, useReceipts, useSummary } from "../../api/queries";
import { ItemCell } from "../../components/ItemCell";
import { SpendBarChart } from "../../components/charts/SpendBarChart";
import { ReceiptsTable } from "../../components/ReceiptsTable";
import { SyncButton } from "../../components/SyncButton";
import { Card, Delta, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

export function DashboardPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const navigate = useNavigate();
  const summary = useSummary();
  const monthly = useMonthly("12");
  const latest = useReceipts({ page: 1 });
  const prices = usePriceWatch();

  const s = summary.data;
  const current = s ? Number(s.current_month.total) : 0;
  const previous = s ? Number(s.previous_month.total) : 0;
  const average = s ? Number(s.average_month_12) : 0;
  const vsAverage = average ? ((current - average) / average) * 100 : 0;

  return (
    <div className="page">
      <PageHeader title={t("dashboard.title")} subtitle={t("dashboard.subtitle")} actions={<SyncButton />} />

      {summary.isError && <ErrorState onRetry={() => summary.refetch()} />}

      {s && (s.pending.needs_review > 0 || s.pending.error > 0) && (
        <div className={`alert ${s.pending.error ? "critical" : ""}`}>
          {t("dashboard.pendingAlert", { review: s.pending.needs_review, error: s.pending.error })}{" "}
          <Link to={`/receipts?status=${s.pending.error ? "error" : "needs_review"}`}>{t("dashboard.review")}</Link>
        </div>
      )}

      <div className="grid grid-4">
        {s ? (
          <>
            <StatTile
              label={t("dashboard.thisMonth", { month: f.monthLong(s.current_month.month, false) })}
              value={f.currency(current)}
              foot={
                <>
                  {average > 0 && <Delta value={vsAverage} label={f.percent(vsAverage)} />}
                  <span>{t("dashboard.vsAverage")}</span>
                </>
              }
            />
            <StatTile
              label={t("dashboard.lastMonth", { month: f.monthLong(s.previous_month.month, false) })}
              value={f.currency(previous)}
              foot={t("dashboard.receiptsCount", { count: s.previous_month.receipts })}
            />
            <StatTile
              label={t("dashboard.monthlyAverage")}
              value={f.currency(average)}
              foot={t("dashboard.last12")}
            />
            <StatTile
              label={t("dashboard.allTime")}
              value={f.currency(s.all_time.total)}
              foot={t("dashboard.receiptsCount", { count: s.all_time.receipts })}
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

      <div className="grid grid-main">
        <Card
          title={t("dashboard.chartTitle")}
          subtitle={t("dashboard.chartSubtitle")}
          actions={<Link to="/spending">{t("dashboard.seeSpending")}</Link>}
        >
          {monthly.data ? (
            <SpendBarChart
              ariaLabel={t("dashboard.chartTitle")}
              data={monthly.data.map((m) => ({
                key: m.month,
                value: Number(m.total),
                extra: t("dashboard.receiptsCount", { count: m.receipts }),
              }))}
              onSelect={(month) => navigate(`/spending?month=${month}`)}
            />
          ) : (
            <Loading rows={6} />
          )}
        </Card>

        <Card title={t("dashboard.syncTitle")}>
          {s ? (
            s.last_sync ? (
              <dl className="kv">
                <dt>{t("dashboard.lastSync")}</dt>
                <dd>{f.dateTime(s.last_sync.finished_at ?? s.last_sync.started_at)}</dd>
                <dt>{t("dashboard.result")}</dt>
                <dd>
                  <span className={`badge ${s.last_sync.status === "success" ? "good" : s.last_sync.status === "failed" ? "critical" : "info"}`}>
                    {t(`job.${s.last_sync.status}`)}
                  </span>
                </dd>
                <dt>{t("dashboard.newReceipts")}</dt>
                <dd className="num">{s.last_sync.stats.receipts_created ?? 0}</dd>
              </dl>
            ) : (
              <p className="muted">{t("dashboard.neverSynced")}</p>
            )
          ) : (
            <Loading />
          )}
          <p className="muted" style={{ fontSize: 13 }}>{t("dashboard.syncHint")}</p>
          <SyncButton primary />
        </Card>
      </div>

      <Card
        title={t("dashboard.priceAlerts")}
        subtitle={t("dashboard.priceAlertsSubtitle")}
        actions={<Link to="/prices">{t("dashboard.seeAll")}</Link>}
      >
        {!prices.data && <Loading rows={4} />}
        {prices.data && prices.data.alerts.length === 0 && <p className="muted">{t("prices.noAlerts")}</p>}
        {prices.data && prices.data.alerts.length > 0 && (
          <div className="table-wrap">
            <table>
              <tbody>
                {prices.data.alerts.slice(0, 5).map((a) => (
                  <tr key={a.key}>
                    <td className="wrap"><ItemCell item={a} /></td>
                    <td className="right num secondary">
                      {t("prices.paidVsNow", { paid: f.currency(a.last_paid), now: f.currency(a.catalog_price) })}
                    </td>
                    <td className="right num">
                      <Delta value={Number(a.diff_pct)} label={f.percent(a.diff_pct ?? 0)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={t("dashboard.latestReceipts")} actions={<Link to="/receipts">{t("dashboard.seeAll")}</Link>}>
        {latest.data ? <ReceiptsTable receipts={latest.data.results.slice(0, 6)} /> : <Loading rows={5} />}
      </Card>
    </div>
  );
}
