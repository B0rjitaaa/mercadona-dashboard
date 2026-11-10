from celery import shared_task

from .models import Receipt
from .services import process_receipt


@shared_task
def parse_receipt(receipt_id: int) -> str:
    receipt = Receipt.objects.get(pk=receipt_id)
    return process_receipt(receipt).status
