import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Scheduled jobs (section 9 of docs/functional-requirements.md), in TIME_ZONE local time.
app.conf.beat_schedule = {
    # Catalogue first, so the receipts imported at 07:00 are matched against fresh data
    "sync-catalog-daily": {
        "task": "products.sync_catalog",
        "schedule": crontab(
            hour=int(os.environ.get("CATALOG_SYNC_HOUR", "6")),
            minute=int(os.environ.get("CATALOG_SYNC_MINUTE", "0")),
        ),
    },
    "sync-gmail-daily": {
        "task": "gmail_sync.sync_gmail",
        "schedule": crontab(
            hour=int(os.environ.get("GMAIL_SYNC_HOUR", "7")),
            minute=int(os.environ.get("GMAIL_SYNC_MINUTE", "0")),
        ),
    },
}
