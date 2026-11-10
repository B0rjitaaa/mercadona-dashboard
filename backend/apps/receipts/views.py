from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Receipt
from .serializers import ReceiptDetailSerializer, ReceiptListSerializer, ReceiptUploadSerializer
from .services import DuplicateReceiptError, create_receipt
from .tasks import parse_receipt


class ReceiptViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Receipts (FR-02, FR-03, FR-08).

    Query params for the list: status, store, date_from, date_to (YYYY-MM-DD), search.
    """

    def get_serializer_class(self):
        if self.action == "list":
            return ReceiptListSerializer
        if self.action == "upload":
            return ReceiptUploadSerializer
        return ReceiptDetailSerializer

    def get_queryset(self):
        qs = (
            Receipt.objects.select_related("store")
            .annotate(line_count=Count("lines"))
            .order_by("-issued_at", "-created_at")
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("lines")

        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("store"):
            qs = qs.filter(store_id=value)
        if value := parse_date(params.get("date_from", "")):
            qs = qs.filter(issued_at__date__gte=value)
        if value := parse_date(params.get("date_to", "")):
            qs = qs.filter(issued_at__date__lte=value)
        if value := params.get("search"):
            qs = qs.filter(
                Q(lines__description__icontains=value) | Q(invoice_number__icontains=value)
            ).distinct()
        return qs

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def upload(self, request):
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            receipt = create_receipt(serializer.validated_data["file"])
        except DuplicateReceiptError as exc:
            return Response(
                {"detail": "Receipt already uploaded.", "id": exc.existing.pk},
                status=status.HTTP_409_CONFLICT,
            )
        parse_receipt.delay(receipt.pk)
        receipt.refresh_from_db()
        return Response(
            ReceiptDetailSerializer(receipt, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):
        receipt = self.get_object()
        parse_receipt.delay(receipt.pk)
        return Response({"id": receipt.pk, "queued": True}, status=status.HTTP_202_ACCEPTED)

    def perform_destroy(self, instance):
        instance.pdf.delete(save=False)
        instance.delete()
