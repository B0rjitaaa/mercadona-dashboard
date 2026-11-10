import { useTranslation } from "react-i18next";
import { useGmailStatus, useJobs } from "../../api/queries";
import { SyncButton } from "../../components/SyncButton";
import { Card, Loading, PageHeader } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

export function SettingsPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const gmail = useGmailStatus();
  const jobs = useJobs();
  const g = gmail.data;

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

      <Card title={t("settings.jobsTitle")}>
        {jobs.data ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("settings.started")}</th>
                  <th>{t("settings.job")}</th>
                  <th>{t("settings.result")}</th>
                  <th className="right">{t("settings.messages")}</th>
                  <th className="right">{t("settings.created")}</th>
                  <th className="right">{t("settings.duplicates")}</th>
                  <th>{t("settings.error")}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.results.map((j) => (
                  <tr key={j.id}>
                    <td>{f.dateTime(j.started_at)}</td>
                    <td className="secondary">{j.job}</td>
                    <td>
                      <span className={`badge ${j.status === "success" ? "good" : j.status === "failed" ? "critical" : "info"}`}>
                        {t(`job.${j.status}`)}
                      </span>
                    </td>
                    <td className="right num">{j.stats.new_messages ?? "—"}</td>
                    <td className="right num">{j.stats.receipts_created ?? "—"}</td>
                    <td className="right num">{j.stats.duplicates ?? "—"}</td>
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
