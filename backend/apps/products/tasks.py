from celery import shared_task

from .catalog import sync_catalog
from .services import match_descriptions


@shared_task(name="products.sync_catalog")
def sync_catalog_task() -> dict:
    run = sync_catalog()
    result = {"job_run": run.pk, "status": run.status, **run.stats}
    if run.status == "success":
        match_products_task.delay()
    return result


@shared_task(name="products.match_products")
def match_products_task(descriptions: list[str] | None = None) -> dict:
    run = match_descriptions(descriptions)
    return {"job_run": run.pk, "status": run.status, **run.stats}
