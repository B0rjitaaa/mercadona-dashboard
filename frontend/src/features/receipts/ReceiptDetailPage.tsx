import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useDeleteReceipt, useReceipt, useReprocessReceipt } from "../../api/queries";
import type { ReceiptDetail } from "../../api/types";
import { Icon } from "../../components/Icon";
import { ProductThumb, itemPath } from "../../components/ProductThumb";
import { Card, ErrorState, KindBadge, Loading, PageHeader, StatusBadge } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

function Actions({ receipt }: { receipt: ReceiptDetail }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const reprocess = useReprocessReceipt(receipt.id);
  const remove = useDeleteReceipt(receipt.id);
  return (
    <>
      <a className="btn" href={receipt.pdf} target="_blank" rel="noreferrer">
        <Icon name="file" />
        {t("receipt.openPdf")}
      </a>
      <button onClick={() => reprocess.mutate()} disabled={reprocess.isPending}>
        <Icon name="refresh" />
        {reprocess.isSuccess ? t("receipt.reprocessQueued") : t("receipt.reprocess")}
      </button>
      <button
        className="btn-danger"
        disabled={remove.isPending}
        onClick={async () => {
          if (window.confirm(t("receipt.deleteConfirm"))) {
            await remove.mutateAsync();
            navigate("/receipts");
          }
        }}
      >
        <Icon name="trash" />
        {t("receipt.delete")}
      </button>
    </>
  );
}

export function ReceiptDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const f = useFormatters();
  const query = useReceipt(id);
  const r = query.data;

  if (query.isError) return <div className="page"><ErrorState onRetry={() => query.refetch()} /></div>;
  if (!r) return <div className="page"><Loading rows={10} /></div>;

  const linesTotal = r.lines.reduce((s, l) => s + Number(l.amount), 0);

  return (
    <div className="page">
      <Link to="/receipts" className="secondary" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        <Icon name="back" /> {t("receipt.back")}
      </Link>
      <PageHeader
        title={
          <span style={{ display: "inline-flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            {f.dateTime(r.issued_at ?? r.created_at)} <StatusBadge status={r.status} /> <KindBadge kind={r.kind} />
          </span>
        }
        subtitle={r.store ? `${r.store.address} · ${r.store.postal_code} ${r.store.city}` : undefined}
        actions={<Actions receipt={r} />}
      />

      {r.error_message && <div className="alert critical">{r.error_message}</div>}
      {r.warnings.length > 0 && (
        <div className="alert">
          <strong>{t("receipt.warnings")}</strong>
          <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
            {r.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-main">
        <Card title={t("receipt.lines", { count: r.lines.length })}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="right">{t("receipt.quantity")}</th>
                  <th>{t("receipt.description")}</th>
                  <th className="right">{t("receipt.unitPrice")}</th>
                  <th className="right">{t("receipt.amount")}</th>
                </tr>
              </thead>
              <tbody>
                {r.lines.map((l) => (
                  <tr key={l.id}>
                    <td className="right num">{f.quantity(l.quantity, l.unit)}</td>
                    <td className="wrap">
                      {l.line_type === "product" ? (
                        <span className="item-cell">
                          <ProductThumb src={l.product_thumbnail} />
                          <span>
                            <Link to={itemPath({ product_id: l.product, description: l.description, name: l.description })}>
                              {l.description}
                            </Link>
                            <small>
                              {l.product_name ?? <span className="badge warning">{t("products.unidentified")}</span>}
                            </small>
                          </span>
                        </span>
                      ) : (
                        <>
                          {l.description} <span className="badge plain">{t(`lineType.${l.line_type}`)}</span>
                        </>
                      )}
                    </td>
                    <td className="right num secondary">
                      {f.currency(l.unit_price)}
                      {l.unit === "kg" && "/kg"}
                    </td>
                    <td className="right num">{f.currency(l.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td />
                  <td>{t("receipt.total")}</td>
                  <td />
                  <td className="right num">{f.currency(r.total ?? linesTotal)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>

        <div className="grid" style={{ alignContent: "start" }}>
          <Card title={t("receipt.details")}>
            <dl className="kv">
              <dt>{r.kind === "return" ? t("receipt.returnNumber") : t("receipt.invoice")}</dt>
              <dd className="num">{r.invoice_number ?? "—"}</dd>
              {r.original_invoice_number && (
                <>
                  <dt>{t("receipt.originalInvoice")}</dt>
                  <dd className="num">{r.original_invoice_number}</dd>
                </>
              )}
              <dt>{t("receipt.operation")}</dt>
              <dd className="num">{r.operation_number || "—"}</dd>
              <dt>{t("receipts.payment")}</dt>
              <dd>{r.payment_method || "—"}</dd>
              <dt>{t("receipt.store")}</dt>
              <dd>{r.store ? `${r.store.code} · ${r.store.city}` : "—"}</dd>
              <dt>{t("receipt.source")}</dt>
              <dd>{t(`source.${r.source}`)}</dd>
            </dl>
          </Card>

          {r.vat_breakdown.length > 0 && (
            <Card title={t("receipt.vat")}>
              <table>
                <thead>
                  <tr>
                    <th>{t("receipt.vatRate")}</th>
                    <th className="right">{t("receipt.vatBase")}</th>
                    <th className="right">{t("receipt.vatTax")}</th>
                  </tr>
                </thead>
                <tbody>
                  {r.vat_breakdown.map((v) => (
                    <tr key={v.rate}>
                      <td className="num">{v.rate}%</td>
                      <td className="right num">{f.currency(v.base)}</td>
                      <td className="right num">{f.currency(v.tax)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
