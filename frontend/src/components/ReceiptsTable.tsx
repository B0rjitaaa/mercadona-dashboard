import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReceiptSummary } from "../api/types";
import { useFormatters } from "../i18n/format";
import { KindBadge, StatusBadge } from "./ui";

export function ReceiptsTable({ receipts, compact = false }: { receipts: ReceiptSummary[]; compact?: boolean }) {
  const { t } = useTranslation();
  const f = useFormatters();
  const navigate = useNavigate();

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{t("receipts.date")}</th>
            {!compact && <th>{t("receipts.store")}</th>}
            <th className="right">{t("receipts.items")}</th>
            <th className="right">{t("receipts.total")}</th>
            {!compact && <th>{t("receipts.payment")}</th>}
            <th>{t("receipts.status")}</th>
          </tr>
        </thead>
        <tbody>
          {receipts.map((r) => (
            <tr key={r.id} className="clickable" onClick={() => navigate(`/receipts/${r.id}`)}>
              <td>
                <a href={`/receipts/${r.id}`} onClick={(e) => e.preventDefault()}>
                  {f.dateTime(r.issued_at ?? r.created_at)}
                </a>{" "}
                <KindBadge kind={r.kind} />
              </td>
              {!compact && <td className="secondary">{r.store ? r.store.address : "—"}</td>}
              <td className="right num">{r.line_count}</td>
              <td className="right num">{f.currency(r.total)}</td>
              {!compact && <td className="secondary">{r.payment_method || "—"}</td>}
              <td>
                <StatusBadge status={r.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
