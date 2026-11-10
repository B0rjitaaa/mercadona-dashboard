from celery import shared_task

from .report import send_weekly


@shared_task(name="reports.weekly_report")
def weekly_report_task() -> dict:
    run = send_weekly()
    return {"status": run.status, **run.stats}
