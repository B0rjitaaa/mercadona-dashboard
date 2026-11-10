from django.core.management.base import BaseCommand

from apps.receipts.models import Receipt
from apps.receipts.services import process_receipt


class Command(BaseCommand):
    help = "Re-run the parser on stored receipts (e.g. after a parser improvement)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            choices=Receipt.Status.values,
            help="Only receipts with this status (default: all).",
        )

    def handle(self, *args, status: str | None, **options):
        receipts = Receipt.objects.order_by("pk")
        if status:
            receipts = receipts.filter(status=status)

        results: dict[str, int] = {}
        for receipt in receipts:
            new_status = process_receipt(receipt).status
            results[new_status] = results.get(new_status, 0) + 1
            if new_status == Receipt.Status.ERROR:
                self.stderr.write(f"#{receipt.pk}: {receipt.error_message}")

        self.stdout.write(self.style.SUCCESS(f"Reprocessed: {results or 'nothing to do'}"))
