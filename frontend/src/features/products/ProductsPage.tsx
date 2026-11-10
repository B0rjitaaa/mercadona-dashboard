import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useItems } from "../../api/queries";
import { Sparkline } from "../../components/charts/Sparkline";
import { ItemCell } from "../../components/ItemCell";
import { itemPath } from "../../components/ProductThumb";
import { Card, Delta, EmptyState, ErrorState, Loading, PageHeader } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

const SORTS = ["spent", "purchases", "recent", "price_change", "name"] as const;
const PAGE = 100;

export function ProductsPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const sort = params.get("sort") ?? "spent";
  const limit = Number(params.get("limit") ?? PAGE);
  const items = useItems(search, sort);

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "limit") next.delete("limit");
    setParams(next, { replace: true });
  };
  const rows = items.data ?? [];

  return (
    <div className="page">
      <PageHeader title={t("products.title")} subtitle={t("products.subtitle")} />
      <Card>
        <div className="filters" style={{ marginBottom: 14 }}>
          <input
            type="search"
            placeholder={t("products.searchPlaceholder")}
            defaultValue={search}
            onKeyDown={(e) => e.key === "Enter" && set("search", e.currentTarget.value.trim())}
            onBlur={(e) => e.currentTarget.value.trim() !== search && set("search", e.currentTarget.value.trim())}
            aria-label={t("products.searchPlaceholder")}
          />
          <label className="filters secondary">
            {t("products.sortBy")}
            <select value={sort} onChange={(e) => set("sort", e.target.value)}>
              {SORTS.map((s) => (
                <option key={s} value={s}>
                  {t(`products.sort.${s}`)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {items.isError && <ErrorState onRetry={() => items.refetch()} />}
        {items.isLoading && <Loading rows={10} />}
        {items.data && rows.length === 0 && <EmptyState>{t("products.empty")}</EmptyState>}
        {rows.length > 0 && (
          <>
            <p className="muted" style={{ marginTop: 0 }}>{t("products.count", { count: rows.length })}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("products.name")}</th>
                    <th className="right">{t("products.purchases")}</th>
                    <th className="right">{t("products.spent")}</th>
                    <th className="right">{t("products.lastPrice")}</th>
                    <th className="right">{t("products.change")}</th>
                    <th>{t("products.trend")}</th>
                    <th>{t("products.lastPurchase")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, limit).map((item) => {
                    const pct = Number(item.price_change_pct ?? 0);
                    return (
                      <tr key={item.key} className="clickable" onClick={() => navigate(itemPath(item))}>
                        <td className="wrap">
                          <ItemCell item={item} />
                        </td>
                        <td className="right num">{item.purchases}</td>
                        <td className="right num">{f.currency(item.spent)}</td>
                        <td className="right num">
                          {f.currency(item.last_price)}
                          {item.unit === "kg" && "/kg"}
                        </td>
                        <td className="right num">
                          {item.purchases > 1 && pct !== 0 ? (
                            <Delta value={pct} label={f.percent(pct)} />
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                        <td>
                          <Sparkline values={item.trend.map(Number)} />
                        </td>
                        <td className="secondary">{f.date(item.last_purchase)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {rows.length > limit && (
              <div style={{ textAlign: "center", marginTop: 12 }}>
                <button onClick={() => set("limit", String(limit + PAGE))}>
                  {t("products.showMore", { count: rows.length - limit })}
                </button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
