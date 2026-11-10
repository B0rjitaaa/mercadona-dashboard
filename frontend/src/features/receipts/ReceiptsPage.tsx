import { useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../api/client";
import { useReceipts, useUploadReceipt } from "../../api/queries";
import { Icon } from "../../components/Icon";
import { ReceiptsTable } from "../../components/ReceiptsTable";
import { Card, EmptyState, ErrorState, Loading, PageHeader, Pagination } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

const FILTER_KEYS = ["search", "status", "kind", "date_from", "date_to"] as const;

function UploadButton() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const upload = useUploadReceipt();
  const [message, setMessage] = useState("");

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    setMessage("");
    try {
      const receipt = await upload.mutateAsync(file);
      navigate(`/receipts/${receipt.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        navigate(`/receipts/${(error.body as { id: number }).id}`);
      } else {
        setMessage(t("receipts.uploadError"));
      }
    } finally {
      if (input.current) input.current.value = "";
    }
  };

  return (
    <>
      <input ref={input} type="file" accept="application/pdf" hidden onChange={(e) => onFile(e.target.files?.[0])} />
      <button onClick={() => input.current?.click()} disabled={upload.isPending}>
        <Icon name="upload" />
        {upload.isPending ? t("receipts.uploading") : t("receipts.upload")}
      </button>
      {message && <span className="delta bad">{message}</span>}
    </>
  );
}

export function ReceiptsPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? "1");
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""])) as Record<
    (typeof FILTER_KEYS)[number],
    string
  >;
  const receipts = useReceipts({ ...filters, page });

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next, { replace: true });
  };
  const hasFilters = FILTER_KEYS.some((k) => filters[k]);
  const data = receipts.data;
  const pageTotal = data?.results.reduce((s, r) => s + Number(r.total ?? 0), 0) ?? 0;

  return (
    <div className="page">
      <PageHeader title={t("receipts.title")} subtitle={t("receipts.subtitle")} actions={<UploadButton />} />

      <Card>
        <div className="filters" style={{ marginBottom: 14 }}>
          <input
            type="search"
            placeholder={t("receipts.searchPlaceholder")}
            defaultValue={filters.search}
            onKeyDown={(e) => e.key === "Enter" && set("search", e.currentTarget.value.trim())}
            onBlur={(e) => e.currentTarget.value.trim() !== filters.search && set("search", e.currentTarget.value.trim())}
            aria-label={t("receipts.searchPlaceholder")}
          />
          <select value={filters.status} onChange={(e) => set("status", e.target.value)} aria-label={t("receipts.status")}>
            <option value="">{t("receipts.allStatuses")}</option>
            {(["processed", "needs_review", "error", "pending"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.${s}`)}
              </option>
            ))}
          </select>
          <select value={filters.kind} onChange={(e) => set("kind", e.target.value)} aria-label={t("receipts.kind")}>
            <option value="">{t("receipts.allKinds")}</option>
            <option value="sale">{t("kind.sale")}</option>
            <option value="return">{t("kind.return")}</option>
          </select>
          <label className="filters secondary">
            {t("receipts.from")}
            <input type="date" value={filters.date_from} onChange={(e) => set("date_from", e.target.value)} />
          </label>
          <label className="filters secondary">
            {t("receipts.to")}
            <input type="date" value={filters.date_to} onChange={(e) => set("date_to", e.target.value)} />
          </label>
          {hasFilters && (
            <button className="btn-ghost" onClick={() => setParams({}, { replace: true })}>
              {t("receipts.clear")}
            </button>
          )}
        </div>

        {receipts.isError && <ErrorState onRetry={() => receipts.refetch()} />}
        {!data && receipts.isLoading && <Loading rows={8} />}
        {data && data.results.length === 0 && <EmptyState>{t("receipts.empty")}</EmptyState>}
        {data && data.results.length > 0 && (
          <>
            <p className="muted" style={{ marginTop: 0 }}>
              {t("receipts.resultCount", { count: data.count })}
              {data.count <= 50 && ` · ${t("receipts.sum", { total: f.currency(pageTotal) })}`}
            </p>
            <ReceiptsTable receipts={data.results} />
            <Pagination page={page} count={data.count} onChange={(p) => set("page", String(p))} />
          </>
        )}
      </Card>
    </div>
  );
}
