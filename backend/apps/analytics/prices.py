"""Price watch for the products you buy regularly (FR-05 alerts, FR-10).

For each regular product (linked to the catalogue, bought at least REGULAR_MIN_PURCHASES
times, last time within REGULAR_WITHIN_DAYS):
- catalogue price now vs the price you paid last time, with the yearly impact if you
  keep buying the same quantity;
- the latest catalogue price change, if any;
- personal inflation: catalogue price now vs what you paid about a year ago, weighted
  by your spend on each product over the last 12 months.

Variable-weight products (trays of meat, cheese wedges, bags of fruit: `approx_size` in
the catalogue) cost a different amount per tray, and the receipt does not say how much it
weighed, so they are never compared with the price paid: only their catalogue price per
kg is followed. A difference above SUSPICIOUS_PCT is more likely a wrong link than a real
price change, so it is reported separately for the user to check.
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.products.models import CatalogPrice, Product

from .services import ZERO, _item_identity, product_lines

REGULAR_MIN_PURCHASES = 3
REGULAR_WITHIN_DAYS = 180
ALERT_MIN_PCT = Decimal("1")
SUSPICIOUS_PCT = Decimal("40")
YEAR_AGO_WINDOW_DAYS = (330, 400)  # "about a year ago"


def _pct(new: Decimal, old: Decimal) -> Decimal | None:
    return ((new - old) / old * 100).quantize(Decimal("0.1")) if old else None


def price_watch(recent_days: int = 30) -> dict:
    now = timezone.now()
    year_ago = now - timedelta(days=365)
    lines = (
        product_lines()
        .filter(product__isnull=False, product__is_manual=False)
        .select_related("receipt")
        .order_by("receipt__issued_at", "position")
    )
    by_product: dict[int, list] = defaultdict(list)
    for line in lines:
        by_product[line.product_id].append(line)

    regular = {
        pid: rows
        for pid, rows in by_product.items()
        if len({r.receipt_id for r in rows}) >= REGULAR_MIN_PURCHASES
        and (now - rows[-1].receipt.issued_at).days <= REGULAR_WITHIN_DAYS
    }
    products = {
        p.pk: p
        for p in Product.objects.filter(pk__in=regular).select_related("category__parent__parent")
    }
    history: dict[int, list[CatalogPrice]] = defaultdict(list)
    for price in CatalogPrice.objects.filter(product_id__in=regular).order_by("date"):
        history[price.product_id].append(price)

    rows, inflation_parts = [], []
    for pid, plines in regular.items():
        product = products[pid]
        last = plines[-1]
        unit = last.unit
        variable = bool((product.raw.get("price_instructions") or {}).get("approx_size"))
        per_kg = unit == "kg" or variable
        catalog = product.bulk_price if per_kg and product.bulk_price else product.unit_price
        if catalog is None:
            continue

        last_year = [line for line in plines if line.receipt.issued_at >= year_ago]
        quantity_12m = sum((line.quantity for line in last_year), Decimal("0"))
        spent_12m = sum((line.amount for line in last_year), ZERO)
        diff = None if variable else catalog - last.unit_price

        change = {"catalog_previous": None, "catalog_changed_at": None, "catalog_change_pct": None}
        prices = history[pid]
        if len(prices) >= 2:
            prev, cur = prices[-2], prices[-1]
            prev_value = prev.bulk_price if per_kg and prev.bulk_price else prev.unit_price
            change = {
                "catalog_previous": prev_value,
                "catalog_changed_at": cur.date.isoformat(),
                "catalog_change_pct": _pct(catalog, prev_value),
            }

        # Inflation: average price paid about a year ago vs catalogue price now
        lo, hi = YEAR_AGO_WINDOW_DAYS
        then = [
            line.unit_price for line in plines if lo <= (now - line.receipt.issued_at).days <= hi
        ]
        if then and spent_12m and not variable:
            then_avg = sum(then, ZERO) / len(then)
            inflation_parts.append((spent_12m, catalog / then_avg - 1))

        rows.append(
            {
                **_item_identity(product, ""),
                "unit": unit,
                "variable_weight": variable,
                "catalog_per_kg": per_kg,
                "purchases": len({line.receipt_id for line in plines}),
                "quantity_12m": quantity_12m,
                "spent_12m": spent_12m,
                "last_paid": last.unit_price,
                "last_paid_at": last.receipt.issued_at,
                "catalog_price": catalog,
                "diff": diff,
                "diff_pct": None if variable else _pct(catalog, last.unit_price),
                "impact_12m": None if variable else (diff * quantity_12m).quantize(Decimal("0.01")),
                "is_active": product.is_active,
                **change,
            }
        )

    compared = [r for r in rows if r["diff_pct"] is not None]
    check_links = [r for r in compared if abs(r["diff_pct"]) >= SUSPICIOUS_PCT]
    alerts = [r for r in compared if ALERT_MIN_PCT <= abs(r["diff_pct"]) < SUSPICIOUS_PCT]
    alerts.sort(key=lambda r: (-abs(r["impact_12m"]), r["name"]))
    check_links.sort(key=lambda r: -abs(r["diff_pct"]))
    since = (timezone.localdate() - timedelta(days=recent_days)).isoformat()
    recent = [r for r in rows if r["catalog_changed_at"] and r["catalog_changed_at"] >= since]
    recent.sort(
        key=lambda r: (r["catalog_changed_at"], abs(r["catalog_change_pct"] or 0)), reverse=True
    )

    weight = sum((w for w, _ in inflation_parts), ZERO)
    inflation = (
        (sum((w * change for w, change in inflation_parts), ZERO) / weight * 100).quantize(
            Decimal("0.1")
        )
        if weight
        else None
    )
    up = [r for r in alerts if r["diff"] > 0]
    down = [r for r in alerts if r["diff"] < 0]
    return {
        "regular_products": len(rows),
        "summary": {
            "up": len(up),
            "down": len(down),
            "impact_12m": sum((r["impact_12m"] for r in alerts), ZERO),
            "inflation_12m": inflation,
            "inflation_products": len(inflation_parts),
        },
        "alerts": alerts,
        "check_links": check_links,
        "recent_changes": recent,
        "recent_days": recent_days,
        "rules": {
            "min_purchases": REGULAR_MIN_PURCHASES,
            "within_days": REGULAR_WITHIN_DAYS,
            "min_pct": ALERT_MIN_PCT,
            "suspicious_pct": SUSPICIOUS_PCT,
        },
    }
