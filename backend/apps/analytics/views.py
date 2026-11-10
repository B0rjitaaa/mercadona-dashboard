from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.core.models import JobRun
from apps.core.serializers import JobRunSerializer

from . import prices, services
from .filters import parse_period, parse_sections

MAX_WEEKLY = timedelta(days=366)


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
    """?from=&to=&sections= (FR-14), or the legacy ?months=6|12|24|all (default 12)."""
    params = request.query_params
    period, sections = parse_period(params), parse_sections(params)
    value = params.get("months", "12")
    if period.start or period.end or value == "all":
        months = None
    elif value.isdigit() and 1 <= int(value) <= 240:
        months = int(value)
    else:
        raise ValidationError({"months": "Expected a number between 1 and 240, or 'all'."})
    return Response(_json(services.monthly_spend(months, period, sections)))


@api_view(["GET"])
def weekly(request):
    """?from=&to=&sections=: spend per week, for short periods such as a month."""
    params = request.query_params
    period = parse_period(params)
    if not period.start or (period.end or timezone.localdate()) - period.start > MAX_WEEKLY:
        raise ValidationError({"from": "The weekly view needs a start and covers at most a year."})
    return Response(_json(services.weekly_spend(period, parse_sections(params))))


@api_view(["GET"])
def overview(request):
    """?from=&to=&sections=: totals, top items and sections for a period (FR-14)."""
    params = request.query_params
    return Response(_json(services.overview(parse_period(params), parse_sections(params))))


@api_view(["GET"])
def compare(request):
    """?a_from=&a_to=&b_from=&b_to=&sections=: period A against baseline B (FR-14)."""
    params = request.query_params
    a, b = parse_period(params, "a_"), parse_period(params, "b_")
    if not (a.start and a.end and b.start and b.end):
        raise ValidationError({"detail": "a_from, a_to, b_from and b_to are required."})
    return Response(_json(services.compare(a, b, parse_sections(params))))


@api_view(["GET"])
def top_items(request):
    month = _parse_month(request.query_params.get("month"))
    return Response(_json(services.top_items(month)))


@api_view(["GET"])
def items(request):
    """?search=&sort=spent|purchases|recent|price_change|name&from=&to=&sections=
    &status=identified|unidentified&min_purchases=N&trend=up|down"""
    params = request.query_params
    status = params.get("status", "")
    trend = params.get("trend", "")
    min_purchases = params.get("min_purchases", "1")
    if status and status not in services.ITEM_STATUSES:
        raise ValidationError({"status": f"Expected one of {', '.join(services.ITEM_STATUSES)}."})
    if trend and trend not in services.PRICE_TRENDS:
        raise ValidationError({"trend": "Expected 'up' or 'down'."})
    if not min_purchases.isdigit() or int(min_purchases) < 1:
        raise ValidationError({"min_purchases": "Expected a positive number."})
    rows = services.items(
        search=params.get("search", ""),
        sort=params.get("sort", "spent"),
        period=parse_period(params),
        sections=parse_sections(params),
        status=status,
        min_purchases=int(min_purchases),
        trend=trend,
    )
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
    """?month=YYYY-MM, or ?from=&to= (default: all time). Each section carries its id,
    used by the section filter (FR-14)."""
    month = request.query_params.get("month")
    return Response(
        _json(
            services.categories(
                _parse_month(month) if month else None, parse_period(request.query_params)
            )
        )
    )


@api_view(["GET"])
def price_watch(request):
    """?days=30: window for "recent catalogue changes"."""
    value = request.query_params.get("days", "30")
    if not value.isdigit() or not 1 <= int(value) <= 365:
        raise ValidationError({"days": "Expected a number between 1 and 365."})
    return Response(_json(prices.price_watch(int(value))))
