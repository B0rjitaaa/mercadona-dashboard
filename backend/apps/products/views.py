from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.models import JobRun
from apps.core.serializers import JobRunSerializer

from . import services
from .catalog import JOB_NAME as CATALOG_JOB
from .models import MatchSuggestion, Product, ProductAlias
from .serializers import (
    DescriptionSerializer,
    LinkSerializer,
    ManualProductSerializer,
    ProductSummarySerializer,
)
from .tasks import match_products_task, sync_catalog_task

PRODUCT_QS = Product.objects.select_related("category__parent__parent")


@api_view(["GET"])
def review_list(request):
    """Unidentified receipt descriptions with their suggested products (FR-04)."""
    stats = (
        services.product_lines()
        .exclude(description__in=ProductAlias.objects.values("description"))
        .order_by()
        .values("description")
        .annotate(
            purchases=Count("receipt", distinct=True),
            spent=Sum("amount"),
            last_purchase=Max("receipt__issued_at"),
        )
        .order_by("-spent")
    )
    suggestions: dict[str, list] = {}
    for s in MatchSuggestion.objects.filter(
        description__in=[r["description"] for r in stats]
    ).select_related("product__category__parent__parent"):
        suggestions.setdefault(s.description, []).append(
            {"score": str(s.score), "product": ProductSummarySerializer(s.product).data}
        )

    rows = []
    for row in stats:
        paid, unit = services.latest_paid(row["description"])
        rows.append(
            {
                **row,
                "spent": str(row["spent"]),
                "last_price": str(paid) if paid is not None else None,
                "unit": unit,
                "suggestions": suggestions.get(row["description"], []),
            }
        )
    return Response(rows)


@api_view(["POST"])
def review_link(request):
    data = LinkSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    product = get_object_or_404(Product, pk=data.validated_data["product_id"])
    alias = services.link(data.validated_data["description"], product, ProductAlias.Source.MANUAL)
    return Response({"description": alias.description, "product_id": product.pk})


@api_view(["POST"])
def review_unlink(request):
    data = DescriptionSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    description = data.validated_data["description"]
    services.unlink(description)
    match_products_task.delay([description])  # refresh its suggestions
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def review_manual(request):
    data = ManualProductSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    product = services.create_manual_product(
        data.validated_data["description"], data.validated_data["name"]
    )
    return Response(ProductSummarySerializer(product).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def review_rematch(request):
    result = match_products_task.delay()
    return Response({"task_id": result.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def catalog_search(request):
    query = request.query_params.get("q", "").strip()
    if len(query) < 2:
        return Response([])
    ids = services.build_matcher(include_inactive=True).search(query, limit=20)
    products = {p.id: p for p in PRODUCT_QS.filter(id__in=ids)}
    return Response(ProductSummarySerializer([products[i] for i in ids], many=True).data)


@api_view(["GET"])
def catalog_status(request):
    last = JobRun.objects.filter(job=CATALOG_JOB).first()
    return Response(
        {
            "products": Product.objects.filter(is_manual=False).count(),
            "active": Product.objects.filter(is_manual=False, is_active=True).count(),
            "manual": Product.objects.filter(is_manual=True).count(),
            "aliases": ProductAlias.objects.count(),
            "unmatched": len(services.unmatched_descriptions()),
            "last_sync": JobRunSerializer(last).data if last else None,
        }
    )


@api_view(["POST"])
def catalog_sync(request):
    result = sync_catalog_task.delay()
    return Response({"task_id": result.id}, status=status.HTTP_202_ACCEPTED)
