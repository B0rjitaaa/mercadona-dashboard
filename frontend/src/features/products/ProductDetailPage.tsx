import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useItem } from "../../api/queries";
import { PriceChart } from "../../components/charts/PriceChart";
import { SpendBarChart } from "../../components/charts/SpendBarChart";
import { Icon } from "../../components/Icon";
import { Card, Delta, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

export function ProductDetailPage() {
  const { description = "" } = useParams();
  const { t } = useTranslation();
  const f = useFormatters();
  const query = useItem(description);
  const item = query.data;

  if (query.isError) return <div className="page"><ErrorState onRetry={() => query.refetch()} /></div>;
  if (!item) return <div className="page"><Loading rows={10} /></div>;

  const perUnit = item.unit === "kg" ? "/kg" : "";
  const pct = Number(item.price_change_pct ?? 0);

  return (
    <div className="page">
      <Link to="/products" className="secondary" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        <Icon name="back" /> {t("product.back")}
      </Link>
      <PageHeader
        title={item.description}
        subtitle={t("product.subtitle", { first: f.date(item.first_purchase), last: f.date(item.last_purchase) })}
      />

      <div className="grid grid-4">
        <StatTile
          label={t("product.timesBought")}
          value={item.purchases}
          foot={
            item.frequency_days
              ? t("product.every", { count: item.frequency_days })
              : t("product.quantity", { quantity: f.quantity(item.quantity, item.unit) })
          }
        />
        <StatTile label={t("product.totalSpent")} value={f.currency(item.spent)} foot={t("product.quantity", { quantity: f.quantity(item.quantity, item.unit) })} />
        <StatTile
          label={t("product.currentPrice")}
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
          label={t("product.priceRange")}
          value={`${f.currency(item.min_price)} – ${f.currency(item.max_price)}`}
          foot={t("product.average", { price: f.currency(item.average_price) })}
        />
      </div>

      <Card title={t("product.priceTitle")} subtitle={t("product.priceSubtitle")}>
        <PriceChart
          ariaLabel={t("product.priceTitle")}
          unitSuffix={perUnit}
          data={item.history.map((h) => ({ t: new Date(h.date).getTime(), price: Number(h.unit_price) }))}
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
    </div>
  );
}
