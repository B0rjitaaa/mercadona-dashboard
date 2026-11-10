import os

from celery import Celery
from celery.schedules import crontab  # noqa: F401

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Scheduled jobs (section 9 of docs/functional-requirements.md).
# Enabled as each roadmap phase is implemented.
app.conf.beat_schedule = {
    # "sync-gmail": {
    #     "task": "apps.gmail_sync.tasks.sync_gmail",
    #     "schedule": crontab(hour=7, minute=0),
    # },
    # "update-catalog-prices": {
    #     "task": "apps.products.tasks.update_catalog_prices",
    #     "schedule": crontab(hour=6, minute=0),
    # },
}
