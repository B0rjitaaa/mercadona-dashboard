import { useTranslation } from "react-i18next";
import { Card, EmptyState, PageHeader } from "../../components/ui";

export function ReviewPage() {
  const { t } = useTranslation();
  return (
    <div className="page">
      <PageHeader title={t("review.title")} subtitle={t("review.subtitle")} />
      <Card>
        <EmptyState>{t("review.comingSoon")}</EmptyState>
      </Card>
    </div>
  );
}
