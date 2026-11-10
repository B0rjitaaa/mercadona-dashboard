import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiGet } from "../../api/client";

export function DashboardPage() {
  const { t } = useTranslation();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<{ status: string }>("/health/"),
  });

  const status = health.isLoading
    ? t("dashboard.checking")
    : health.isError
      ? t("dashboard.offline")
      : t("dashboard.online");

  return (
    <>
      <h1>{t("dashboard.title")}</h1>
      <p>
        {t("dashboard.backend")}: {status}
      </p>
    </>
  );
}
