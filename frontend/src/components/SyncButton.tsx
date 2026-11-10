import { useTranslation } from "react-i18next";
import { useSyncNow } from "../api/queries";
import { Icon } from "./Icon";

export function SyncButton({ primary = false }: { primary?: boolean }) {
  const { t } = useTranslation();
  const sync = useSyncNow();
  return (
    <button className={primary ? "btn-primary" : ""} onClick={() => sync.mutate()} disabled={sync.isPending}>
      <Icon name="refresh" />
      {sync.isPending ? t("sync.running") : sync.isSuccess ? t("sync.queued") : t("sync.now")}
    </button>
  );
}
