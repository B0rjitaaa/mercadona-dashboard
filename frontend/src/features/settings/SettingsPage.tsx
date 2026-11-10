import { useTranslation } from "react-i18next";
import { useCatalogStatus, useCatalogSync, useGmailStatus, useJobs, useReportStatus, useSendReport } from "../../api/queries";
import { Icon } from "../../components/Icon";
import { SyncButton } from "../../components/SyncButton";
import { Card, Loading, PageHeader } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

export function SettingsPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const gmail = useGmailStatus();
  const jobs = useJobs();
  const g = gmail.data;
  const catalog = useCatalogStatus();
  const catalogSync = useCatalogSync();
  const c = catalog.data;
  const report = useReportStatus();
  const sendReport = useSendReport();
  const r = report.data;
  const statLabel = (key: string) => t(`settings.stat.${key}`, { defaultValue: key });

  return (
    <div className="page">
      <PageHeader title={t("settings.title")} subtitle={t("settings.subtitle")} />
      <Card title={t("settings.gmailTitle")} actions={<SyncButton primary />}>
        {g ? (
          <dl className="kv">
            <dt>{t("settings.credentials")}</dt>
            <dd>
              <span className={`badge ${g.credentials_configured ? "good" : "critical"}`}>
                {g.credentials_configured ? t("settings.yes") : t("settings.no")}
              </span>
            </dd>
            <dt>{t("settings.authorised")}</dt>
            <dd>
              <span className={`badge ${g.authorised ? "good" : "critical"}`}>
                {g.authorised ? t("settings.yes") : t("settings.notAuthorised")}
              </span>
            </dd>
            <dt>{t("settings.query")}</dt>
            <dd>
              <code>{g.query}</code>
            </dd>
            <dt>{t("settings.schedule")}</dt>
            <dd>{t("settings.scheduleValue")}</dd>
          </dl>
        ) : (
          <Loading />
        )}
      </Card>

      <Card
        title={t("settings.catalogTitle")}
        actions={
          <button onClick={() => catalogSync.mutate()} disabled={catalogSync.isPending || c?.last_sync?.status === "running"}>
            <Icon name="refresh" />
            {catalogSync.isSuccess || c?.last_sync?.status === "running" ? t("settings.catalogSyncQueued") : t("settings.catalogSync")}
          </button>
        }
      >
        {c ? (
          <dl className="kv">
            <dt>{t("settings.catalogProducts")}</dt>
            <dd className="num">{t("settings.catalogProductsValue", { total: c.products, active: c.active })}</dd>
            <dt>{t("settings.catalogLinked")}</dt>
            <dd className="num">{t("settings.catalogLinkedValue", { aliases: c.aliases, unmatched: c.unmatched })}</dd>
            <dt>{t("settings.lastCatalogSync")}</dt>
            <dd>{c.last_sync ? f.dateTime(c.last_sync.finished_at ?? c.last_sync.started_at) : t("settings.never")}</dd>
            <dt>{t("settings.schedule")}</dt>
            <dd>{t("settings.catalogScheduleValue")}</dd>
          </dl>
        ) : (
          <Loading />
        )}
      </Card>

      <Card
        title={t("settings.reportTitle")}
        subtitle={t("settings.reportSubtitle")}
        actions={
          <div className="filters">
            <a className="btn" href="/api/reports/weekly/preview/" target="_blank" rel="noreferrer">
              {t("settings.reportPreview")}
            </a>
            <button
              onClick={() => sendReport.mutate()}
              disabled={!r?.recipient || !r.can_send || sendReport.isPending || r.last_run?.status === "running"}
            >
              {sendReport.isSuccess ? t("settings.reportQueued") : t("settings.reportSend")}
            </button>
          </div>
        }
      >
        {r ? (
          <dl className="kv">
            <dt>{t("settings.reportRecipient")}</dt>
            <dd>{r.recipient ?? <span className="muted">{t("settings.reportNoRecipient")}</span>}</dd>
            <dt>{t("settings.reportSchedule")}</dt>
            <dd>
              {t("settings.reportScheduleValue", {
                day: t(`settings.days.${r.schedule.day}`, { defaultValue: r.schedule.day }),
                time: `${String(r.schedule.hour).padStart(2, "0")}:${String(r.schedule.minute).padStart(2, "0")}`,
              })}
            </dd>
            <dt>{t("settings.reportCanSend")}</dt>
            <dd>
              <span className={`badge ${r.can_send ? "good" : "warning"}`}>
                {r.can_send ? t("settings.yes") : t("settings.reportNeedsAuth")}
              </span>
            </dd>
            <dt>{t("settings.reportLast")}</dt>
            <dd>
              {r.last_run ? (
                <>
                  {f.dateTime(r.last_run.finished_at ?? r.last_run.started_at)}{" "}
                  <span className={`badge ${r.last_run.status === "success" ? "good" : r.last_run.status === "failed" ? "critical" : "info"}`}>
                    {t(`job.${r.last_run.status}`)}
                  </span>
                  {r.last_run.error && <div className="muted" style={{ fontSize: 13 }}>{r.last_run.error}</div>}
                </>
              ) : (
                t("settings.never")
              )}
            </dd>
          </dl>
        ) : (
          <Loading />
        )}
      </Card>

      <Card title={t("settings.jobsTitle")}>
        {jobs.data ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("settings.started")}</th>
                  <th>{t("settings.job")}</th>
                  <th>{t("settings.result")}</th>
                  <th>{t("settings.details")}</th>
                  <th>{t("settings.error")}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.results.map((j) => (
                  <tr key={j.id}>
                    <td>{f.dateTime(j.started_at)}</td>
                    <td className="secondary">{t(`settings.jobName.${j.job}`, { defaultValue: j.job })}</td>
                    <td>
                      <span className={`badge ${j.status === "success" ? "good" : j.status === "failed" ? "critical" : "info"}`}>
                        {t(`job.${j.status}`)}
                      </span>
                    </td>
                    <td className="wrap secondary" style={{ fontSize: 13 }}>
                      {Object.entries(j.stats)
                        .filter(([, v]) => v)
                        .map(([k, v]) => `${statLabel(k)}: ${f.number(v)}`)
                        .join(" · ") || "—"}
                    </td>
                    <td className="wrap secondary">{j.error || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Loading rows={4} />
        )}
      </Card>
    </div>
  );
}
