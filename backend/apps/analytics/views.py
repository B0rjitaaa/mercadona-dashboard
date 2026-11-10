from datetime import datetime
from decimal import Decimal

from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.core.models import JobRun
from apps.core.serializers import JobRunSerializer

from . import prices, services


def _json(value):
    """Decimals as exact strings, like the rest of the API (COERCE_DECIMAL_TO_STRING)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json(v) for v in value]
    return value


def _parse_month(value: str | None):
    if not value:
        return services.month_start(datetime.now().date())
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError as exc:
        raise ValidationError({"month": "Expected YYYY-MM."}) from exc


@api_view(["GET"])
def summary(request):
    data = services.summary()
    last_sync = JobRun.objects.filter(job="sync_gmail").first()
    data["last_sync"] = JobRunSerializer(last_sync).data if last_sync else None
    return Response(_json(data))


@api_view(["GET"])
def monthly(request):
    """?months=6|12|24 (default 12) or ?months=all."""
    value = request.query_params.get("months", "12")
    if value == "all":
        months = None
    elif value.isdigit() and 1 <= int(value) <= 240:
        months = int(value)
    else:
        raise ValidationError({"months": "Expected a number between 1 and 240, or 'all'."})
    return Response(_json(services.monthly_spend(months)))


@api_view(["GET"])
def top_items(request):
    month = _parse_month(request.query_params.get("month"))
    return Response(_json(services.top_items(month)))


@api_view(["GET"])
def items(request):
    """?search=&sort=spent|purchases|recent|price_change|name"""
    params = request.query_params
    rows = services.items(search=params.get("search", ""), sort=params.get("sort", "spent"))
    return Response(_json(rows))


@api_view(["GET"])
def item_detail(request):
    """An unidentified item, by receipt description."""
    description = request.query_params.get("description", "")
    data = services.item_detail(description=description) if description else None
    if data is None:
        raise NotFound("Item not found.")
    return Response(_json(data))


@api_view(["GET"])
def product_detail(request, product_id: int):
    data = services.item_detail(product_id=product_id)
    if data is None:
        raise NotFound("Product not found.")
    return Response(_json(data))


@api_view(["GET"])
def categories(request):
    """?month=YYYY-MM (default: all time)."""
    month = request.query_params.get("month")
    return Response(_json(services.categories(_parse_month(month) if month else None)))


@api_view(["GET"])
def price_watch(request):
    """?days=30: window for "recent catalogue changes"."""
    value = request.query_params.get("days", "30")
    if not value.isdigit() or not 1 <= int(value) <= 365:
        raise ValidationError({"days": "Expected a number between 1 and 365."})
    return Response(_json(prices.price_watch(int(value))))
