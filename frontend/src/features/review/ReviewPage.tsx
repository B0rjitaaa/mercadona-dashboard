import { useTranslation } from "react-i18next";

export function ReviewPage() {
  const { t } = useTranslation();
  return <h1>{t("review.title")}</h1>;
}
