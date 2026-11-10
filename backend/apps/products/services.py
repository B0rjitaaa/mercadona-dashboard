"""Linking receipt descriptions to products (FR-04)."""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import JobRun
from apps.receipts.models import Receipt, ReceiptLine

from .matching import CatalogItem, Matcher, is_confident
from .models import MatchSuggestion, Product, ProductAlias

logger = logging.getLogger(__name__)
JOB_NAME = "match_products"
SUGGESTIONS = 3


def product_lines() -> "ReceiptLine.objects":
    return ReceiptLine.objects.filter(line_type=ReceiptLine.LineType.PRODUCT)


def build_matcher(include_inactive: bool = False) -> Matcher:
    products = Product.objects.all()
    if not include_inactive:
        products = products.filter(Q(is_active=True) | Q(is_manual=True))
    return Matcher(
        [
            CatalogItem(p.id, p.name, p.packaging, p.unit_price, p.bulk_price)
            for p in products.only("id", "name", "packaging", "unit_price", "bulk_price")
        ]
    )


@transaction.atomic
def link(
    description: str, product: Product, source: str, score: Decimal | None = None
) -> ProductAlias:
    alias, _ = ProductAlias.objects.update_or_create(
        description=description, defaults={"product": product, "source": source, "score": score}
    )
    product_lines().filter(description=description).update(product=product)
    MatchSuggestion.objects.filter(description=description).delete()
    return alias


@transaction.atomic
def unlink(description: str) -> None:
    ProductAlias.objects.filter(description=description).delete()
    product_lines().filter(description=description).update(product=None)


def apply_aliases(receipt: Receipt) -> int:
    """Set the product of a receipt's lines whose description already has an alias."""
    linked = 0
    aliases = dict(
        ProductAlias.objects.filter(
            description__in=receipt.lines.values_list("description", flat=True)
        ).values_list("description", "product_id")
    )
    for line in receipt.lines.filter(line_type=ReceiptLine.LineType.PRODUCT):
        if line.description in aliases:
            line.product_id = aliases[line.description]
            line.save(update_fields=["product"])
            linked += 1
    return linked


def unmatched_descriptions() -> list[str]:
    return list(
        product_lines()
        .exclude(description__in=ProductAlias.objects.values("description"))
        .order_by("description")  # clear the model ordering, or DISTINCT keeps duplicates
        .values_list("description", flat=True)
        .distinct()
    )


def latest_paid(description: str) -> tuple[Decimal | None, str]:
    line = (
        product_lines()
        .filter(description=description)
        .order_by("-receipt__issued_at")
        .values("unit_price", "unit")
        .first()
    )
    return (line["unit_price"], line["unit"]) if line else (None, "unit")


def match_descriptions(descriptions: list[str] | None = None) -> JobRun:
    """Auto-link confident matches and store suggestions for the rest."""
    run = JobRun.objects.create(job=JOB_NAME)
    stats = {"checked": 0, "auto_linked": 0, "suggested": 0, "no_candidates": 0}
    try:
        if not Product.objects.exists():
            run.error = "Catalogue is empty: run the catalogue sync first."
        else:
            matcher = build_matcher()
            known = set(ProductAlias.objects.values_list("description", flat=True))
            todo = [d for d in (descriptions or unmatched_descriptions()) if d not in known]
            products = {p.id: p for p in Product.objects.filter(id__in=matcher.items)}
            for description in todo:
                stats["checked"] += 1
                paid, unit = latest_paid(description)
                candidates = matcher.candidates(description, paid, unit, limit=SUGGESTIONS)
                if is_confident(candidates):
                    best = candidates[0]
                    link(description, products[best.item_id], ProductAlias.Source.AUTO, best.score)
                    stats["auto_linked"] += 1
                    continue
                with transaction.atomic():
                    MatchSuggestion.objects.filter(description=description).delete()
                    MatchSuggestion.objects.bulk_create(
                        MatchSuggestion(
                            description=description,
                            product_id=c.item_id,
                            score=c.score,
                            rank=rank,
                        )
                        for rank, c in enumerate(candidates, 1)
                    )
                stats["suggested" if candidates else "no_candidates"] += 1
        run.status = JobRun.Status.SUCCESS
    except Exception as exc:
        logger.exception("Product matching failed")
        run.status = JobRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
    finally:
        run.stats = stats
        run.finished_at = timezone.now()
        run.save()
    return run


def create_manual_product(description: str, name: str) -> Product:
    product = Product.objects.create(name=name.strip() or description, is_manual=True)
    link(description, product, ProductAlias.Source.MANUAL)
    return product
