import { useTranslation } from "react-i18next";

export function ReceiptsPage() {
  const { t } = useTranslation();
  return <h1>{t("receipts.title")}</h1>;
}
