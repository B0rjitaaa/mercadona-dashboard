"""Aggregation queries over receipts (FR-06, FR-07, FR-09, FR-10).

Until products are identified (phase 3), an "item" is a receipt description.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count, Max, Min, Q, QuerySet, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.receipts.models import Receipt, ReceiptLine

ZERO = Decimal("0.00")
COUNTED_STATUSES = (Receipt.Status.PROCESSED, Receipt.Status.NEEDS_REVIEW)


def counted_receipts() -> QuerySet[Receipt]:
    """Receipts whose amounts are trusted enough to be included in totals."""
    return Receipt.objects.filter(status__in=COUNTED_STATUSES, issued_at__isnull=False)


def product_lines() -> QuerySet[ReceiptLine]:
    return ReceiptLine.objects.filter(
        receipt__in=counted_receipts(), line_type=ReceiptLine.LineType.PRODUCT
    )


def month_start(value: date) -> date:
    return value.replace(day=1)


def add_months(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def monthly_spend(months: int | None = 12) -> list[dict]:
    """Spend per month, contiguous (months without receipts are zero), oldest first.

    `months=None` returns every month since the first receipt.
    """
    rows = (
        counted_receipts()
        .annotate(month=TruncMonth("issued_at"))
        .values("month")
        .annotate(total=Sum("total"), receipts=Count("id"))
    )
    # TruncMonth on a DateTimeField returns aware datetimes in the current time zone
    by_month = {month_key(row["month"].date()): row for row in rows}
    current = month_start(timezone.localdate())

    if months is None:
        start = min((row["month"].date() for row in rows), default=current)
    else:
        start = add_months(current, -(months - 1))

    result = []
    month = start
    while month <= current:
        row = by_month.get(month_key(month), {})
        total = row.get("total") or ZERO
        receipts = row.get("receipts") or 0
        result.append(
            {
                "month": month_key(month),
                "total": total,
                "receipts": receipts,
                "average_receipt": (total / receipts).quantize(Decimal("0.01"))
                if receipts
                else ZERO,
            }
        )
        month = add_months(month, 1)
    return result


def summary() -> dict:
    months = monthly_spend(13)
    current, previous, history = months[-1], months[-2], months[:-1]
    active = [m for m in history if m["receipts"]]
    average = (
        (sum((m["total"] for m in active), ZERO) / len(active)).quantize(Decimal("0.01"))
        if active
        else ZERO
    )
    pending = Receipt.objects.aggregate(
        needs_review=Count("id", filter=Q(status=Receipt.Status.NEEDS_REVIEW)),
        error=Count("id", filter=Q(status=Receipt.Status.ERROR)),
    )
    totals = counted_receipts().aggregate(total=Sum("total"), receipts=Count("id"))
    return {
        "current_month": current,
        "previous_month": previous,
        "average_month_12": average,
        "all_time": {"total": totals["total"] or ZERO, "receipts": totals["receipts"]},
        "pending": pending,
    }


def _section_name(product) -> str | None:
    node = product.category if product else None
    while node is not None and node.parent_id:
        node = node.parent
    return node.name if node else None


def _item_identity(product, description: str) -> dict:
    """Linked lines are grouped by product, unidentified ones by receipt description."""
    if product is not None:
        return {
            "key": f"p{product.pk}",
            "product_id": product.pk,
            "name": product.name,
            "packaging": product.packaging,
            "thumbnail": product.thumbnail,
            "section": _section_name(product),
            "description": None,
        }
    return {
        "key": f"d:{description}",
        "product_id": None,
        "name": description,
        "packaging": "",
        "thumbnail": "",
        "section": None,
        "description": description,
    }


def _products_by_id(ids) -> dict:
    from apps.products.models import Product

    return {
        p.pk: p
        for p in Product.objects.filter(pk__in=[i for i in ids if i]).select_related(
            "category__parent__parent"
        )
    }


def _grouped(lines, aggregates: dict) -> list[dict]:
    """Aggregate lines per item (product, or description when unidentified)."""
    linked = lines.filter(product__isnull=False).values("product").annotate(**aggregates)
    unlinked = lines.filter(product__isnull=True).values("description").annotate(**aggregates)
    products = _products_by_id([row["product"] for row in linked])
    rows = []
    for row in linked:
        rows.append({**_item_identity(products[row.pop("product")], ""), **row})
    for row in unlinked:
        rows.append({**_item_identity(None, row.pop("description")), **row})
    return rows


def top_items(month: date, limit: int = 10) -> dict:
    lines = product_lines().filter(
        receipt__issued_at__date__gte=month, receipt__issued_at__date__lt=add_months(month, 1)
    )
    rows = _grouped(
        lines,
        {
            "spent": Sum("amount"),
            "purchases": Count("receipt", distinct=True),
            "quantity": Sum("quantity"),
        },
    )
    return {
        "month": month_key(month),
        "by_spend": sorted(rows, key=lambda r: (-r["spent"], r["name"]))[:limit],
        "by_purchases": sorted(rows, key=lambda r: (-r["purchases"], -r["spent"], r["name"]))[
            :limit
        ],
    }


def categories(month: date | None = None) -> dict:
    """Spend per catalogue section (FR-07). Unidentified lines are grouped under None."""
    lines = product_lines()
    if month:
        lines = lines.filter(
            receipt__issued_at__date__gte=month, receipt__issued_at__date__lt=add_months(month, 1)
        )
    rows = (
        lines.values("product__category__parent__parent__name")
        .annotate(spent=Sum("amount"), items=Count("id"))
        .order_by("-spent")
    )
    total = sum((r["spent"] for r in rows), ZERO)
    return {
        "month": month_key(month) if month else None,
        "total": total,
        "sections": [
            {
                "section": r["product__category__parent__parent__name"],
                "spent": r["spent"],
                "share": (r["spent"] / total * 100).quantize(Decimal("0.1")) if total else ZERO,
                "items": r["items"],
            }
            for r in rows
        ],
    }


def _price_stats(prices: list[Decimal]) -> dict:
    first, last = prices[0], prices[-1]
    return {
        "first_price": first,
        "last_price": last,
        "price_change": last - first,
        "price_change_pct": ((last - first) / first * 100).quantize(Decimal("0.1"))
        if first
        else None,
    }


def items(search: str = "", sort: str = "spent") -> list[dict]:
    lines = product_lines()
    if search:
        lines = lines.filter(Q(description__icontains=search) | Q(product__name__icontains=search))

    rows = _grouped(
        lines,
        {
            "purchases": Count("receipt", distinct=True),
            "quantity": Sum("quantity"),
            "spent": Sum("amount"),
            "first_purchase": Min("receipt__issued_at"),
            "last_purchase": Max("receipt__issued_at"),
            "min_price": Min("unit_price"),
            "max_price": Max("unit_price"),
        },
    )

    history: dict[str, list] = defaultdict(list)
    ordered = lines.order_by("receipt__issued_at", "position").values_list(
        "product_id", "description", "unit_price", "unit"
    )
    for product_id, description, price, unit in ordered:
        key = f"p{product_id}" if product_id else f"d:{description}"
        history[key].append((price, unit))

    result = []
    for row in rows:
        prices = [price for price, _ in history[row["key"]]]
        result.append(
            {
                **row,
                "unit": history[row["key"]][-1][1],
                **_price_stats(prices),
                "trend": prices[-12:],
            }
        )

    sorters = {
        "spent": lambda r: (-r["spent"], r["name"]),
        "purchases": lambda r: (-r["purchases"], -r["spent"]),
        "recent": lambda r: (-r["last_purchase"].timestamp(), r["name"]),
        "price_change": lambda r: (-(r["price_change_pct"] or 0), r["name"]),
        "name": lambda r: r["name"],
    }
    return sorted(result, key=sorters.get(sort, sorters["spent"]))


def item_detail(product_id: int | None = None, description: str | None = None) -> dict | None:
    from apps.products.models import Product

    lines = product_lines().select_related("receipt")
    product = None
    if product_id is not None:
        product = (
            Product.objects.filter(pk=product_id)
            .select_related("category__parent__parent")
            .prefetch_related("aliases", "catalog_prices")
            .first()
        )
        if product is None:
            return None
        lines = lines.filter(product=product)
    else:
        lines = lines.filter(description=description, product__isnull=True)

    rows = list(lines.order_by("receipt__issued_at", "position"))
    if not rows and product is None:
        return None

    unit = rows[-1].unit if rows else ("kg" if product and product.size_format == "kg" else "unit")
    data = {
        **_item_identity(product, description or ""),
        "unit": unit,
        "product": None,
        "aliases": [],
        "catalog_prices": [],
        "purchases": 0,
        "quantity": Decimal("0"),
        "spent": ZERO,
        "history": [],
        "monthly": [],
    }
    if product is not None:
        data["product"] = {
            "mercadona_id": product.mercadona_id,
            "share_url": product.share_url,
            "unit_price": product.unit_price,
            "bulk_price": product.bulk_price,
            "reference_price": product.reference_price,
            "reference_format": product.reference_format,
            "is_active": product.is_active,
            "is_manual": product.is_manual,
            "category_path": _category_path(product),
        }
        data["aliases"] = [
            {"description": a.description, "source": a.source, "score": a.score}
            for a in product.aliases.all()
        ]
        data["catalog_prices"] = [
            {
                "date": p.date.isoformat(),
                "price": p.bulk_price if unit == "kg" and p.bulk_price else p.unit_price,
            }
            for p in product.catalog_prices.all()
        ]
    if not rows:
        return data

    prices = [line.unit_price for line in rows]
    dates = [line.receipt.issued_at for line in rows]
    distinct_days = sorted({timezone.localtime(d).date() for d in dates})
    monthly: dict[str, dict] = defaultdict(lambda: {"spent": ZERO, "quantity": Decimal("0")})
    for line in rows:
        key = month_key(timezone.localtime(line.receipt.issued_at).date())
        monthly[key]["spent"] += line.amount
        monthly[key]["quantity"] += line.quantity

    data.update(
        {
            "purchases": len({line.receipt_id for line in rows}),
            "quantity": sum((line.quantity for line in rows), Decimal("0")),
            "spent": sum((line.amount for line in rows), ZERO),
            "first_purchase": dates[0],
            "last_purchase": dates[-1],
            "frequency_days": round(
                (distinct_days[-1] - distinct_days[0]).days / (len(distinct_days) - 1)
            )
            if len(distinct_days) > 1
            else None,
            "min_price": min(prices),
            "max_price": max(prices),
            "average_price": (sum(prices, ZERO) / len(prices)).quantize(Decimal("0.01")),
            **_price_stats(prices),
            "monthly": [{"month": k, **v} for k, v in sorted(monthly.items())],
            "history": [
                {
                    "date": line.receipt.issued_at,
                    "receipt_id": line.receipt_id,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "unit_price": line.unit_price,
                    "amount": line.amount,
                }
                for line in rows
            ],
        }
    )
    return data


def _category_path(product) -> list[str]:
    path, node = [], product.category
    while node is not None:
        path.insert(0, node.name)
        node = node.parent
    return path
