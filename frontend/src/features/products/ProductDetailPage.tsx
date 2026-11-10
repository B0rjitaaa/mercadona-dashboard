import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useItem, useUnlinkDescription } from "../../api/queries";
import { PriceChart } from "../../components/charts/PriceChart";
import { SpendBarChart } from "../../components/charts/SpendBarChart";
import { Icon } from "../../components/Icon";
import { ProductThumb } from "../../components/ProductThumb";
import { Card, Delta, EmptyState, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

export function ProductDetailPage() {
  const { id, description } = useParams();
  const key = id ? `p${id}` : `d:${description ?? ""}`;
  const { t } = useTranslation();
  const f = useFormatters();
  const query = useItem(key);
  const unlink = useUnlinkDescription();
  const item = query.data;

  if (query.isError) return <div className="page"><ErrorState onRetry={() => query.refetch()} /></div>;
  if (!item) return <div className="page"><Loading rows={10} /></div>;

  const perUnit = item.unit === "kg" ? "/kg" : "";
  const pct = Number(item.price_change_pct ?? 0);
  const p = item.product;
  const catalogPrice = p ? (item.unit === "kg" ? p.bulk_price : p.unit_price) : null;

  return (
    <div className="page">
      <Link to="/products" className="secondary" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        <Icon name="back" /> {t("product.back")}
      </Link>

      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <ProductThumb src={item.thumbnail} size="lg" />
        <div style={{ flex: 1, minWidth: 240 }}>
          <PageHeader
            title={item.name}
            subtitle={
              <>
                {p?.category_path.length ? p.category_path.join(" › ") : item.description && t("product.unidentifiedHint")}
                {item.purchases > 0 && (
                  <span className="muted">
                    {" · "}
                    {t("product.subtitle", { first: f.date(item.first_purchase), last: f.date(item.last_purchase) })}
                  </span>
                )}
              </>
            }
            actions={
              p?.share_url ? (
                <a className="btn" href={p.share_url} target="_blank" rel="noreferrer">
                  {t("product.viewInShop")}
                </a>
              ) : !p ? (
                <Link className="btn btn-primary" to={`/review?q=${encodeURIComponent(item.description ?? "")}`}>
                  {t("product.identify")}
                </Link>
              ) : undefined
            }
          />
          {p && !p.is_active && !p.is_manual && (
            <span className="badge warning" style={{ marginTop: 8 }}>{t("product.discontinued")}</span>
          )}
          {p?.is_manual && <span className="badge plain" style={{ marginTop: 8 }}>{t("product.manual")}</span>}
        </div>
      </div>

      {item.purchases === 0 ? (
        <Card><EmptyState>{t("product.noPurchases")}</EmptyState></Card>
      ) : (
        <>
          <div className="grid grid-4">
            <StatTile
              label={t("product.timesBought")}
              value={item.purchases}
              foot={item.frequency_days ? t("product.every", { count: item.frequency_days }) : undefined}
            />
            <StatTile
              label={t("product.totalSpent")}
              value={f.currency(item.spent)}
              foot={t("product.quantity", { quantity: f.quantity(item.quantity, item.unit) })}
            />
            <StatTile
              label={t("product.lastPaid")}
              value={`${f.currency(item.last_price)}${perUnit}`}
              foot={
                item.purchases > 1 ? (
                  <>
                    <Delta value={pct} label={f.percent(pct)} />
                    <span>{t("product.sinceFirst", { price: f.currency(item.first_price) })}</span>
                  </>
                ) : undefined
              }
            />
            <StatTile
              label={catalogPrice ? t("product.catalogPrice") : t("product.priceRange")}
              value={
                catalogPrice
                  ? `${f.currency(catalogPrice)}${perUnit}`
                  : `${f.currency(item.min_price)} – ${f.currency(item.max_price)}`
              }
              foot={
                catalogPrice && p?.reference_price
                  ? `${f.currency(p.reference_price)}/${p.reference_format}`
                  : t("product.average", { price: f.currency(item.average_price) })
              }
            />
          </div>

          <Card title={t("product.priceTitle")} subtitle={t("product.priceSubtitle")}>
            <PriceChart
              ariaLabel={t("product.priceTitle")}
              unitSuffix={perUnit}
              paid={item.history.map((h) => ({ t: new Date(h.date).getTime(), price: Number(h.unit_price) }))}
              catalog={item.catalog_prices.map((c) => ({ t: new Date(c.date).getTime(), price: Number(c.price) }))}
            />
          </Card>

          <div className="grid grid-2">
            <Card title={t("product.monthlyTitle")}>
              <SpendBarChart
                ariaLabel={t("product.monthlyTitle")}
                height={220}
                data={item.monthly.map((m) => ({
                  key: m.month,
                  value: Number(m.spent),
                  extra: t("product.quantity", { quantity: f.quantity(m.quantity, item.unit) }),
                }))}
              />
            </Card>

            <Card title={t("product.historyTitle", { count: item.history.length })}>
              <div className="table-wrap" style={{ maxHeight: 260, overflowY: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>{t("receipts.date")}</th>
                      {item.aliases.length > 1 && <th>{t("receipt.description")}</th>}
                      <th className="right">{t("receipt.quantity")}</th>
                      <th className="right">{t("receipt.unitPrice")}</th>
                      <th className="right">{t("receipt.amount")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...item.history].reverse().map((h, i) => (
                      <tr key={`${h.receipt_id}-${i}`}>
                        <td>
                          <Link to={`/receipts/${h.receipt_id}`}>{f.date(h.date)}</Link>
                        </td>
                        {item.aliases.length > 1 && <td className="secondary">{h.description}</td>}
                        <td className="right num">{f.quantity(h.quantity, h.unit)}</td>
                        <td className="right num">
                          {f.currency(h.unit_price)}
                          {perUnit}
                        </td>
                        <td className="right num">{f.currency(h.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}

      {item.aliases.length > 0 && (
        <Card title={t("product.aliasesTitle")} subtitle={t("product.aliasesSubtitle")}>
          <div className="table-wrap">
            <table>
              <tbody>
                {item.aliases.map((a) => (
                  <tr key={a.description}>
                    <td><code>{a.description}</code></td>
                    <td className="secondary">
                      {a.source === "auto"
                        ? t("product.aliasAuto", { score: f.percent(Number(a.score ?? 0) * 100, false) })
                        : t("product.aliasManual")}
                    </td>
                    <td className="right">
                      <button
                        className="btn-ghost btn-danger"
                        disabled={unlink.isPending}
                        onClick={() => window.confirm(t("product.unlinkConfirm")) && unlink.mutate(a.description)}
                      >
                        {t("product.unlink")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
