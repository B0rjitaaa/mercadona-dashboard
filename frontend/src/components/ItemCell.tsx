import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ItemIdentity } from "../api/types";
import { ProductThumb, itemPath } from "./ProductThumb";

export function ItemCell({ item, link = true }: { item: ItemIdentity; link?: boolean }) {
  const { t } = useTranslation();
  const name = link ? (
    <Link to={itemPath(item)} onClick={(e) => e.stopPropagation()}>
      {item.name}
    </Link>
  ) : (
    item.name
  );
  return (
    <span className="item-cell">
      <ProductThumb src={item.thumbnail} />
      <span>
        {name}
        <small>
          {item.product_id ? (
            [item.packaging, item.section].filter(Boolean).join(" · ")
          ) : (
            <span className="badge warning">{t("products.unidentified")}</span>
          )}
        </small>
      </span>
    </span>
  );
}
