import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { ReceiptKind, ReceiptStatus } from "../api/types";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="filters">{actions}</div>}
    </header>
  );
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatTile({
  label,
  value,
  foot,
}: {
  label: ReactNode;
  value: ReactNode;
  foot?: ReactNode;
}) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {foot && <div className="stat-foot">{foot}</div>}
    </div>
  );
}

/** Signed change. For spending, going up is bad. */
export function Delta({ value, label, upIsGood = false }: { value: number; label: string; upIsGood?: boolean }) {
  if (!Number.isFinite(value) || value === 0) return <span className="delta">{label}</span>;
  const good = value > 0 === upIsGood;
  return (
    <span className={`delta ${good ? "good" : "bad"}`}>
      {value > 0 ? "▲" : "▼"} {label}
    </span>
  );
}

const STATUS_TONE: Record<ReceiptStatus, string> = {
  processed: "good",
  needs_review: "warning",
  error: "critical",
  pending: "info",
};

export function StatusBadge({ status }: { status: ReceiptStatus }) {
  const { t } = useTranslation();
  return <span className={`badge ${STATUS_TONE[status]}`}>{t(`status.${status}`)}</span>;
}

export function KindBadge({ kind }: { kind: ReceiptKind }) {
  const { t } = useTranslation();
  if (kind === "sale") return null;
  return <span className="badge plain">{t(`kind.${kind}`)}</span>;
}

export function Loading({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }} aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: 18, width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="state">
      <p>{t("common.loadError")}</p>
      {onRetry && <button onClick={onRetry}>{t("common.retry")}</button>}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state">{children}</div>;
}

export function Pagination({
  page,
  count,
  pageSize = 50,
  onChange,
}: {
  page: number;
  count: number;
  pageSize?: number;
  onChange: (page: number) => void;
}) {
  const { t } = useTranslation();
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="filters" style={{ justifyContent: "space-between", marginTop: 12 }}>
      <span className="muted">{t("common.pageOf", { page, pages, count })}</span>
      <div className="filters">
        <button disabled={page <= 1} onClick={() => onChange(page - 1)}>
          {t("common.previous")}
        </button>
        <button disabled={page >= pages} onClick={() => onChange(page + 1)}>
          {t("common.next")}
        </button>
      </div>
    </div>
  );
}
