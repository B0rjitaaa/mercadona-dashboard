import { useTranslation } from "react-i18next";

export function ProductsPage() {
  const { t } = useTranslation();
  return <h1>{t("products.title")}</h1>;
}
