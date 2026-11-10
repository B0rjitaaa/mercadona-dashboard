import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  useCatalogSearch,
  useCatalogStatus,
  useCatalogSync,
  useLinkDescription,
  useManualProduct,
  useRematch,
  useReview,
} from "../../api/queries";
import type { ProductSummary, ReviewItem } from "../../api/types";
import { Icon } from "../../components/Icon";
import { ProductThumb, itemPath } from "../../components/ProductThumb";
import { Card, EmptyState, ErrorState, Loading, PageHeader } from "../../components/ui";
import { useFormatters } from "../../i18n/format";

const PAGE = 15;

function ProductOption({
  product,
  score,
  unit,
  onPick,
  busy,
}: {
  product: ProductSummary;
  score?: string;
  unit: string;
  onPick: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const f = useFormatters();
  const price = unit === "kg" ? product.bulk_price : product.unit_price;
  return (
    <div className="suggestion">
      <ProductThumb src={product.thumbnail} />
      <div className="body">
        <span className="name">{product.name}</span>
        <span className="muted" style={{ fontSize: 12 }}>
          {[product.packaging, price && `${f.currency(price)}${unit === "kg" ? "/kg" : ""}`].filter(Boolean).join(" · ")}
          {!product.is_active && !product.is_manual && ` · ${t("product.discontinued")}`}
        </span>
        <span style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={onPick} disabled={busy}>
            {t("review.pick")}
          </button>
          {score && <span className="muted num" style={{ fontSize: 12 }}>{t("review.score", { score: f.percent(Number(score) * 100, false) })}</span>}
        </span>
      </div>
    </div>
  );
}

function CatalogSearch({ item, onPick, busy }: { item: ReviewItem; onPick: (id: number) => void; busy: boolean }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(item.description);
  const [query, setQuery] = useState(item.description);
  const results = useCatalogSearch(query);
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(draft.trim());
        }}
      >
        <input type="search" value={draft} onChange={(e) => setDraft(e.target.value)} aria-label={t("review.searchCatalog")} autoFocus />
        <button type="submit">{t("review.search")}</button>
      </form>
      {results.isFetching && !results.data && <Loading rows={2} />}
      {results.data && results.data.length === 0 && <span className="muted">{t("review.noResults")}</span>}
      {results.data && results.data.length > 0 && (
        <div className="suggestions search-results">
          {results.data.map((p) => (
            <ProductOption key={p.id} product={p} unit={item.unit} onPick={() => onPick(p.id)} busy={busy} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReviewRow({ item }: { item: ReviewItem }) {
  const { t } = useTranslation();
  const f = useFormatters();
  const link = useLinkDescription();
  const manual = useManualProduct();
  const [searching, setSearching] = useState(item.suggestions.length === 0);
  const busy = link.isPending || manual.isPending;
  const pick = (productId: number) => link.mutate({ description: item.description, product_id: productId });

  return (
    <div className="review-row">
      <div className="review-head">
        <span>
          <code>{item.description}</code>{" "}
          <Link className="muted" style={{ fontSize: 13 }} to={itemPath({ product_id: null, description: item.description, name: item.description })}>
            {t("review.seePurchases")}
          </Link>
        </span>
        <span className="muted num" style={{ fontSize: 13 }}>
          {t("review.stats", {
            count: item.purchases,
            spent: f.currency(item.spent),
            price: `${f.currency(item.last_price)}${item.unit === "kg" ? "/kg" : ""}`,
            date: f.date(item.last_purchase),
          })}
        </span>
      </div>

      {item.suggestions.length > 0 && (
        <div className="suggestions">
          {item.suggestions.map((s) => (
            <ProductOption
              key={s.product.id}
              product={s.product}
              score={s.score}
              unit={item.unit}
              onPick={() => pick(s.product.id)}
              busy={busy}
            />
          ))}
        </div>
      )}

      <div className="filters">
        <button onClick={() => setSearching((v) => !v)}>{searching ? t("review.hideSearch") : t("review.searchCatalog")}</button>
        <button
          className="btn-ghost"
          disabled={busy}
          onClick={() => {
            const name = window.prompt(t("review.manualPrompt"), item.description);
            if (name !== null) manual.mutate({ description: item.description, name });
          }}
        >
          {t("review.notInCatalog")}
        </button>
      </div>
      {searching && <CatalogSearch item={item} onPick={pick} busy={busy} />}
    </div>
  );
}

export function ReviewPage() {
  const { t } = useTranslation();
  const f = useFormatters();
  const [params, setParams] = useSearchParams();
  const filter = params.get("q") ?? "";
  const [limit, setLimit] = useState(PAGE);
  const review = useReview();
  const status = useCatalogStatus();
  const rematch = useRematch();
  const catalogSync = useCatalogSync();

  const rows = (review.data ?? []).filter((r) => r.description.toLowerCase().includes(filter.toLowerCase()));
  const total = (review.data ?? []).reduce((s, r) => s + Number(r.spent), 0);
  const catalogEmpty = status.data && status.data.products === 0;

  return (
    <div className="page">
      <PageHeader
        title={t("review.title")}
        subtitle={
          review.data
            ? t("review.summary", { count: review.data.length, spent: f.currency(total) })
            : t("review.subtitle")
        }
        actions={
          <button onClick={() => rematch.mutate()} disabled={rematch.isPending || catalogEmpty}>
            <Icon name="refresh" />
            {rematch.isSuccess ? t("review.rematchQueued") : t("review.rematch")}
          </button>
        }
      />

      {catalogEmpty && (
        <div className="alert">
          {t("review.catalogEmpty")}{" "}
          <button onClick={() => catalogSync.mutate()} disabled={catalogSync.isPending || catalogSync.isSuccess}>
            {catalogSync.isSuccess ? t("settings.catalogSyncQueued") : t("settings.catalogSync")}
          </button>
        </div>
      )}

      <Card>
        <p className="muted" style={{ marginTop: 0 }}>{t("review.help")}</p>
        <div className="filters" style={{ marginBottom: 4 }}>
          <input
            type="search"
            placeholder={t("review.filter")}
            value={filter}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("q", e.target.value);
              else next.delete("q");
              setParams(next, { replace: true });
            }}
            aria-label={t("review.filter")}
          />
        </div>
        {review.isError && <ErrorState onRetry={() => review.refetch()} />}
        {review.isLoading && <Loading rows={8} />}
        {review.data && rows.length === 0 && <EmptyState>{filter ? t("review.noMatches") : t("review.allDone")}</EmptyState>}
        {rows.slice(0, limit).map((item) => (
          <ReviewRow key={item.description} item={item} />
        ))}
        {rows.length > limit && (
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <button onClick={() => setLimit(limit + PAGE)}>{t("products.showMore", { count: rows.length - limit })}</button>
          </div>
        )}
      </Card>
    </div>
  );
}
