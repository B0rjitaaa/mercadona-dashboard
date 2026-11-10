"""Daily catalogue download: categories, products and price changes (FR-04, FR-05)."""

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.core.models import JobRun
from apps.mercadona.client import CatalogEntry, MercadonaClient

from .models import CatalogPrice, Category, Product

logger = logging.getLogger(__name__)
JOB_NAME = "sync_catalog"


def _decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _upsert_category(data: dict, level: int, parent: Category | None) -> Category:
    category, _ = Category.objects.update_or_create(
        id=data["id"],
        defaults={
            "name": data["name"],
            "level": level,
            "parent": parent,
            "order": data.get("order") or 0,
        },
    )
    return category


def _apply_entry(entry: CatalogEntry, now, today, cache: dict, stats: dict) -> None:
    section = cache.get(("c", entry.section["id"])) or _upsert_category(entry.section, 0, None)
    cache[("c", entry.section["id"])] = section
    category = cache.get(("c", entry.category["id"])) or _upsert_category(
        entry.category, 1, section
    )
    cache[("c", entry.category["id"])] = category
    sub = cache.get(("c", entry.subcategory["id"])) or _upsert_category(
        entry.subcategory, 2, category
    )
    cache[("c", entry.subcategory["id"])] = sub

    data = entry.product
    prices = data.get("price_instructions") or {}
    unit_price = _decimal(prices.get("unit_price"))
    fields = {
        "name": data.get("display_name", "")[:300],
        "packaging": (data.get("packaging") or "")[:100],
        "thumbnail": data.get("thumbnail") or "",
        "share_url": data.get("share_url") or "",
        "category": sub,
        "unit_price": unit_price,
        "bulk_price": _decimal(prices.get("bulk_price")),
        "reference_price": _decimal(prices.get("reference_price")),
        "reference_format": prices.get("reference_format") or "",
        "size_format": prices.get("size_format") or "",
        "unit_size": _decimal(prices.get("unit_size")),
        "is_active": True,
        "last_seen_at": now,
        "raw": data,
    }
    product, created = Product.objects.update_or_create(
        mercadona_id=str(data["id"]), defaults=fields
    )
    stats["products_new" if created else "products_updated"] += 1

    if unit_price is None:
        return
    last = product.catalog_prices.order_by("-date").first()
    if last is None or last.unit_price != unit_price or last.bulk_price != fields["bulk_price"]:
        CatalogPrice.objects.update_or_create(
            product=product,
            date=today,
            defaults={
                "unit_price": unit_price,
                "bulk_price": fields["bulk_price"],
                "reference_price": fields["reference_price"],
            },
        )
        if last is not None:
            stats["price_changes"] += 1


def sync_catalog(client: MercadonaClient | None = None) -> JobRun:
    run = JobRun.objects.create(job=JOB_NAME)
    stats = {
        "products_seen": 0,
        "products_new": 0,
        "products_updated": 0,
        "price_changes": 0,
        "discontinued": 0,
        "category_errors": 0,
    }
    errors: list[str] = []
    started = timezone.now()
    today = timezone.localdate()
    try:
        client = client or MercadonaClient()
        cache: dict = {}
        seen: set[str] = set()
        for entry in client.iter_catalog(errors=errors):
            product_id = str(entry.product["id"])
            if product_id in seen:  # a product can be listed in several subcategories
                continue
            seen.add(product_id)
            with transaction.atomic():
                _apply_entry(entry, started, today, cache, stats)
        stats["products_seen"] = len(seen)
        stats["category_errors"] = len(errors)

        # Only flag discontinued products after a complete download.
        if not errors and seen:
            stats["discontinued"] = (
                Product.objects.filter(is_manual=False, is_active=True)
                .exclude(mercadona_id__in=seen)
                .update(is_active=False)
            )
        run.status = JobRun.Status.SUCCESS
        run.error = "\n".join(errors[:20])
    except Exception as exc:
        logger.exception("Catalogue sync failed")
        run.status = JobRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
    finally:
        run.stats = stats
        run.finished_at = timezone.now()
        run.save()
    return run
