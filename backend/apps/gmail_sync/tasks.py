from celery import shared_task

from .services import SyncAlreadyRunningError, sync_gmail


@shared_task(name="gmail_sync.sync_gmail")
def sync_gmail_task() -> dict:
    try:
        run = sync_gmail()
    except SyncAlreadyRunningError:
        return {"status": "skipped", "reason": "already running"}
    if run.stats.get("receipts_created"):
        from apps.products.tasks import match_products_task

        match_products_task.delay()
    return {"job_run": run.pk, "status": run.status, **run.stats}
