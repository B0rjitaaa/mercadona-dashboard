from celery import shared_task

from .models import Receipt
from .services import process_receipt


@shared_task
def parse_receipt(receipt_id: int) -> str:
    receipt = process_receipt(Receipt.objects.get(pk=receipt_id))
    unmatched = list(
        receipt.lines.filter(line_type="product", product__isnull=True)
        .order_by("description")
        .values_list("description", flat=True)
        .distinct()
    )
    if unmatched:
        from apps.products.tasks import match_products_task

        match_products_task.delay(unmatched)
    return receipt.status
