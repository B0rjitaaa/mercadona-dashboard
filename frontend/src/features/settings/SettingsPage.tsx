import { useTranslation } from "react-i18next";

export function SettingsPage() {
  const { t } = useTranslation();
  return <h1>{t("settings.title")}</h1>;
}
