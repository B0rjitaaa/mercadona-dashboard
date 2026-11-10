import hashlib
from dataclasses import asdict
from typing import BinaryIO

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import Receipt, ReceiptLine, Store
from .parsing import ParsedReceipt, ReceiptParseError, parse_pdf


class DuplicateReceiptError(Exception):
    def __init__(self, existing: Receipt):
        self.existing = existing
        super().__init__(f"Receipt already exists (#{existing.pk})")


def create_receipt(
    file: BinaryIO,
    source: Receipt.Source = Receipt.Source.UPLOAD,
    gmail_message_id: str = "",
) -> Receipt:
    """Store a receipt PDF in 'pending' state. Raises DuplicateReceiptError for known PDFs."""
    content = file.read()
    sha256 = hashlib.sha256(content).hexdigest()

    if existing := Receipt.objects.filter(pdf_sha256=sha256).first():
        raise DuplicateReceiptError(existing)

    receipt = Receipt(pdf_sha256=sha256, source=source, gmail_message_id=gmail_message_id)
    receipt.pdf.save(f"{sha256}.pdf", ContentFile(content), save=False)
    receipt.save()
    return receipt


def process_receipt(receipt: Receipt) -> Receipt:
    """Parse the receipt PDF and (re)build its data. Idempotent."""
    try:
        with receipt.pdf.open("rb") as fh:
            parsed = parse_pdf(fh)
    except ReceiptParseError as exc:
        return _mark_error(receipt, str(exc))

    duplicate = (
        Receipt.objects.filter(invoice_number=parsed.invoice_number).exclude(pk=receipt.pk).first()
    )
    if duplicate:
        return _mark_error(
            receipt, f"Duplicate of receipt #{duplicate.pk} ({parsed.invoice_number})"
        )

    with transaction.atomic():
        _apply_parsed(receipt, parsed)
    return receipt


def _mark_error(receipt: Receipt, message: str) -> Receipt:
    receipt.status = Receipt.Status.ERROR
    receipt.error_message = message
    receipt.parsed_at = timezone.now()
    receipt.save(update_fields=["status", "error_message", "parsed_at", "updated_at"])
    return receipt


def _apply_parsed(receipt: Receipt, parsed: ParsedReceipt) -> None:
    store = None
    if parsed.store_code:
        store, _ = Store.objects.update_or_create(
            chain="mercadona",
            code=parsed.store_code,
            defaults={
                "company_name": parsed.company_name,
                "tax_id": parsed.tax_id,
                "address": parsed.store_address,
                "postal_code": parsed.postal_code,
                "city": parsed.city.upper(),
                "phone": parsed.phone,
            },
        )

    warnings = list(parsed.warnings)
    if not parsed.totals_match:
        warnings.append(f"Lines add up to {parsed.lines_total}, receipt total is {parsed.total}")

    receipt.store = store
    receipt.invoice_number = parsed.invoice_number
    receipt.kind = parsed.kind.value
    receipt.original_invoice_number = parsed.original_invoice_number
    receipt.issued_at = (
        timezone.make_aware(parsed.issued_at, timezone.get_default_timezone())
        if parsed.issued_at
        else None
    )
    receipt.operation_number = parsed.operation_number
    receipt.total = parsed.total
    receipt.payment_method = parsed.payment_method
    receipt.vat_breakdown = [
        {k: str(v) for k, v in asdict(vat).items()} for vat in parsed.vat_breakdown
    ]
    receipt.warnings = warnings
    receipt.status = (
        Receipt.Status.PROCESSED if parsed.totals_match else Receipt.Status.NEEDS_REVIEW
    )
    receipt.error_message = ""
    receipt.parsed_at = timezone.now()
    receipt.save()

    receipt.lines.all().delete()
    ReceiptLine.objects.bulk_create(
        ReceiptLine(
            receipt=receipt,
            position=line.position,
            line_type=line.line_type.value,
            description=line.description,
            quantity=line.quantity,
            unit=line.unit.value,
            unit_price=line.unit_price,
            amount=line.amount,
        )
        for line in parsed.lines
    )
