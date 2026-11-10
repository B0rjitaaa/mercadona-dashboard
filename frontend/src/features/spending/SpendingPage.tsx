import { useTranslation } from "react-i18next";

export function SpendingPage() {
  const { t } = useTranslation();
  return <h1>{t("spending.title")}</h1>;
}
