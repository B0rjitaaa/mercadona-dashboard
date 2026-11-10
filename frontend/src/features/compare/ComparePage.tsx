import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCompare } from "../../api/queries";
import type { ItemChange } from "../../api/types";
import { SectionPicker, useRangeLabel } from "../../components/filters/FilterBar";
import { ProductThumb, itemPath } from "../../components/ProductThumb";
import { Card, Delta, EmptyState, ErrorState, Loading, PageHeader, StatTile } from "../../components/ui";
import { useFormatters } from "../../i18n/format";
import { useFilters } from "../../lib/filters";
import { COMPARISONS, resolveComparison, type Comparison, type ComparisonRanges } from "../../lib/period";

const RANGE_KEYS = ["a_from", "a_to", "b_from", "b_to"] as const;

function ChangeList({ items, empty }: { items: ItemChange[]; empty: string }) {
  const { t } = useTranslation();
  const f = useFormatters();
  if (!items.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ol className="rank">
      {items.map((item) => {
        const diff = Number(item.diff);
        let why: string;
        if (!item.b_purchases) why = t("compare.newItem");
        else if (!item.a_purchases) why = t("compare.droppedItem");
        else
          why = t("compare.effects", {
            price: f.currency(item.price_effect ?? 0),
            quantity: f.currency(item.quantity_effect ?? 0),
          });
        return (
          <li key={item.key}>
            <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
              <ProductThumb src={item.thumbnail} />
              <span style={{ minWidth: 0 }}>
                <Link to={itemPath(item)}>{item.name}</Link>
                <span className="muted" style={{ display: "block", fontSize: 12 }}>
                  {f.currency(item.b_spent)} → {f.currency(item.a_spent)} · {why}
                </span>
              </span>
            </span>
            <Delta value={diff} label={f.currency(Math.abs(diff))} />
          </li>
        );
      })}
    </ol>
  );
}

export function ComparePage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const rangeLabel = useRangeLabel();
  const filters = useFilters();
  const [params, setParams] = useSearchParams();

  const kindParam = params.get("cmp");
  const kind: Comparison = (COMPARISONS as readonly string[]).includes(kindParam ?? "")
    ? (kindParam as Comparison)
    : "month_yoy";
  const preset = resolveComparison(kind === "custom" ? "month_yoy" : kind);
  const ranges: ComparisonRanges =
    kind === "custom"
      ? {
          a: { from: params.get("a_from") || preset.a.from, to: params.get("a_to") || preset.a.to },
          b: { from: params.get("b_from") || preset.b.from, to: params.get("b_to") || preset.b.to },
        }
      : preset;
  const valid = ranges.a.from <= ranges.a.to && ranges.b.from <= ranges.b.to;

  const compare = useCompare(
    valid
      ? {
          a_from: ranges.a.from,
          a_to: ranges.a.to,
          b_from: ranges.b.from,
          b_to: ranges.b.to,
          sections: filters.query.sections,
        }
      : null,
  );
  const c = compare.data;

  const setKind = (next: Comparison) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.set("cmp", next);
        RANGE_KEYS.forEach((k) => p.delete(k));
        if (next === "custom") {
          // Start from the comparison that was on screen
          p.set("a_from", ranges.a.from);
          p.set("a_to", ranges.a.to);
          p.set("b_from", ranges.b.from);
          p.set("b_to", ranges.b.to);
        }
        return p;
      },
      { replace: true },
    );
  const setDate = (key: (typeof RANGE_KEYS)[number], value: string) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.set(key, value);
        return p;
      },
      { replace: true },
    );

  const diff = c ? Number(c.diff) : 0;
  const maxSection = c ? Math.max(...c.sections.flatMap((s) => [Number(s.a), Number(s.b)]), 1) : 1;

  return (
    <div className="page">
      <PageHeader title={t("compare.title")} subtitle={t("compare.subtitle")} />

      <div className="filter-bar">
        <label className="filters secondary">
          {t("compare.kind")}
          <select value={kind} onChange={(e) => setKind(e.target.value as Comparison)}>
            {COMPARISONS.map((k) => (
              <option key={k} value={k}>
                {t(`compare.kinds.${k}`)}
              </option>
            ))}
          </select>
        </label>
        {kind === "custom" &&
          (["a", "b"] as const).map((side) => (
            <div key={side} className="filters">
              <span className="secondary">{t(`compare.${side}`)}</span>
              <input
                type="date"
                aria-label={`${t(`compare.${side}`)} · ${t("filters.from")}`}
                value={ranges[side].from}
                onChange={(e) => setDate(`${side}_from`, e.target.value)}
              />
              <span className="muted">–</span>
              <input
                type="date"
                aria-label={`${t(`compare.${side}`)} · ${t("filters.to")}`}
                value={ranges[side].to}
                onChange={(e) => setDate(`${side}_to`, e.target.value)}
              />
            </div>
          ))}
        <SectionPicker value={filters.sections} onChange={filters.setSections} />
      </div>
      {!valid && <div className="alert">{t("compare.invalid")}</div>}
      {filters.sections.length > 0 && <p className="muted" style={{ margin: 0, fontSize: 13 }}>{t("spending.sectionsNote")}</p>}
      {compare.isError && <ErrorState onRetry={() => compare.refetch()} />}

      <div className="grid grid-4">
        {c ? (
          <>
            <StatTile
              label={t("compare.a")}
              value={f.currency(c.a.total)}
              foot={`${rangeLabel(ranges.a)} · ${t("dashboard.receiptsCount", { count: c.a.receipts })}`}
            />
            <StatTile
              label={t("compare.b")}
              value={f.currency(c.b.total)}
              foot={`${rangeLabel(ranges.b)} · ${t("dashboard.receiptsCount", { count: c.b.receipts })}`}
            />
            <StatTile
              label={t("compare.difference")}
              value={`${diff > 0 ? "+" : ""}${f.currency(diff)}`}
              foot={
                c.diff_pct !== null ? (
                  <Delta value={Number(c.diff_pct)} label={f.percent(c.diff_pct)} />
                ) : (
                  t("compare.noBaseline")
                )
              }
            />
            <StatTile
              label={t("spending.averageReceipt")}
              value={f.currency(c.a.average_receipt)}
              foot={t("compare.before", { value: f.currency(c.b.average_receipt) })}
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

      <Card
        title={t("compare.bySection")}
        subtitle={t("compare.bySectionSubtitle")}
        actions={
          <div className="legend" aria-hidden="true">
            <span>
              <i style={{ background: "var(--series-1)" }} />
              {t("compare.a")}
            </span>
            <span>
              <i style={{ background: "var(--series-1-muted)" }} />
              {t("compare.b")}
            </span>
          </div>
        }
      >
        {!c && <Loading rows={6} />}
        {c && c.sections.length === 0 && <EmptyState>{t("spending.noItems")}</EmptyState>}
        {c && c.sections.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("compare.section")}</th>
                  <th className="right">{t("compare.b")}</th>
                  <th className="right">{t("compare.a")}</th>
                  <th className="right">{t("compare.difference")}</th>
                  <th style={{ width: "28%" }} aria-hidden="true" />
                </tr>
              </thead>
              <tbody>
                {c.sections.map((s) => {
                  const d = Number(s.diff);
                  return (
                    <tr key={s.id ?? "none"}>
                      <td className="wrap">{s.section ?? t("filters.uncategorised")}</td>
                      <td className="right num secondary">{f.currency(s.b)}</td>
                      <td className="right num">{f.currency(s.a)}</td>
                      <td className="right num">
                        <Delta value={d} label={f.currency(Math.abs(d))} />
                      </td>
                      <td aria-hidden="true">
                        <div className="pair-bars">
                          <span style={{ width: `${(Number(s.a) / maxSection) * 100}%` }} />
                          <span className="baseline" style={{ width: `${(Number(s.b) / maxSection) * 100}%` }} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid grid-2">
        <Card title={t("compare.increases")} subtitle={t("compare.effectsHint")}>
          {c ? <ChangeList items={c.increases} empty={t("compare.noIncreases")} /> : <Loading rows={6} />}
        </Card>
        <Card title={t("compare.decreases")}>
          {c ? <ChangeList items={c.decreases} empty={t("compare.noDecreases")} /> : <Loading rows={6} />}
        </Card>
      </div>
      {c && (
        <p className="muted" style={{ fontSize: 13, margin: 0 }}>
          {t("compare.itemsFoot", { new: c.new_items, dropped: c.dropped_items })}
        </p>
      )}
    </div>
  );
}
