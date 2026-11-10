import { Icon } from "./Icon";

export function ProductThumb({ src, size = "md" }: { src?: string | null; size?: "md" | "lg" }) {
  const cls = `thumb ${size === "lg" ? "lg" : ""}`;
  if (!src) {
    return (
      <span className={`${cls} placeholder`} aria-hidden="true">
        <Icon name="box" size={size === "lg" ? 32 : 18} />
      </span>
    );
  }
  return <img className={cls} src={src} alt="" loading="lazy" />;
}

/** URL of an item page: catalogue product or unidentified receipt description. */
export function itemPath(item: { product_id: number | null; description?: string | null; name: string }) {
  return item.product_id
    ? `/products/${item.product_id}`
    : `/products/unidentified/${encodeURIComponent(item.description ?? item.name)}`;
}
