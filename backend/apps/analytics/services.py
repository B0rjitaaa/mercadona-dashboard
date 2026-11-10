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


def top_items(month: date, limit: int = 10) -> dict:
    lines = product_lines().filter(
        receipt__issued_at__date__gte=month, receipt__issued_at__date__lt=add_months(month, 1)
    )
    grouped = lines.values("description").annotate(
        spent=Sum("amount"), purchases=Count("receipt", distinct=True), quantity=Sum("quantity")
    )
    return {
        "month": month_key(month),
        "by_spend": list(grouped.order_by("-spent", "description")[:limit]),
        "by_purchases": list(grouped.order_by("-purchases", "-spent", "description")[:limit]),
    }


def items(search: str = "", sort: str = "spent") -> list[dict]:
    lines = product_lines()
    if search:
        lines = lines.filter(description__icontains=search)

    stats = {
        row["description"]: row
        for row in lines.values("description").annotate(
            purchases=Count("receipt", distinct=True),
            quantity=Sum("quantity"),
            spent=Sum("amount"),
            first_purchase=Min("receipt__issued_at"),
            last_purchase=Max("receipt__issued_at"),
            min_price=Min("unit_price"),
            max_price=Max("unit_price"),
        )
    }

    # First and last unit price per description, plus a short price trend.
    history: dict[str, list] = defaultdict(list)
    for description, price, unit in lines.order_by("receipt__issued_at", "position").values_list(
        "description", "unit_price", "unit"
    ):
        history[description].append((price, unit))

    result = []
    for description, row in stats.items():
        prices = [price for price, _ in history[description]]
        first, last = prices[0], prices[-1]
        result.append(
            {
                **row,
                "unit": history[description][-1][1],
                "first_price": first,
                "last_price": last,
                "price_change": last - first,
                "price_change_pct": ((last - first) / first * 100).quantize(Decimal("0.1"))
                if first
                else None,
                "trend": prices[-12:],
            }
        )

    sorters = {
        "spent": lambda r: (-r["spent"], r["description"]),
        "purchases": lambda r: (-r["purchases"], -r["spent"]),
        "recent": lambda r: (-r["last_purchase"].timestamp(), r["description"]),
        "price_change": lambda r: (-(r["price_change_pct"] or 0), r["description"]),
        "name": lambda r: r["description"],
    }
    return sorted(result, key=sorters.get(sort, sorters["spent"]))


def item_detail(description: str) -> dict | None:
    lines = product_lines().filter(description=description).select_related("receipt")
    rows = list(lines.order_by("receipt__issued_at", "position"))
    if not rows:
        return None

    prices = [line.unit_price for line in rows]
    first, last = prices[0], prices[-1]
    dates = [line.receipt.issued_at for line in rows]
    distinct_days = sorted({timezone.localtime(d).date() for d in dates})
    frequency = (
        round((distinct_days[-1] - distinct_days[0]).days / (len(distinct_days) - 1))
        if len(distinct_days) > 1
        else None
    )

    monthly: dict[str, dict] = defaultdict(lambda: {"spent": ZERO, "quantity": Decimal("0")})
    for line in rows:
        key = month_key(timezone.localtime(line.receipt.issued_at).date())
        monthly[key]["spent"] += line.amount
        monthly[key]["quantity"] += line.quantity

    return {
        "description": description,
        "unit": rows[-1].unit,
        "purchases": len({line.receipt_id for line in rows}),
        "quantity": sum((line.quantity for line in rows), Decimal("0")),
        "spent": sum((line.amount for line in rows), ZERO),
        "first_purchase": dates[0],
        "last_purchase": dates[-1],
        "frequency_days": frequency,
        "first_price": first,
        "last_price": last,
        "min_price": min(prices),
        "max_price": max(prices),
        "average_price": (sum(prices, ZERO) / len(prices)).quantize(Decimal("0.01")),
        "price_change": last - first,
        "price_change_pct": ((last - first) / first * 100).quantize(Decimal("0.1"))
        if first
        else None,
        "monthly": [{"month": k, **v} for k, v in sorted(monthly.items())],
        "history": [
            {
                "date": line.receipt.issued_at,
                "receipt_id": line.receipt_id,
                "quantity": line.quantity,
                "unit": line.unit,
                "unit_price": line.unit_price,
                "amount": line.amount,
            }
            for line in rows
        ],
    }
