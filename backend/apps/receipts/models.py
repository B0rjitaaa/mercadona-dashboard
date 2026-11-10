from django.db import models

from apps.core.models import TimeStampedModel


class Store(TimeStampedModel):
    chain = models.CharField(max_length=50, default="mercadona")
    # Mercadona store number, first block of the invoice number ("1234-001-000001").
    # The printed address varies between receipts, the code does not.
    code = models.CharField(max_length=10)
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=10)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["chain", "code"], name="unique_store_code")]
        ordering = ["chain", "city", "address"]

    def __str__(self) -> str:
        return f"{self.address} ({self.postal_code} {self.city})"


def receipt_upload_path(instance: "Receipt", filename: str) -> str:
    return f"receipts/{instance.pdf_sha256[:2]}/{instance.pdf_sha256}.pdf"


class Receipt(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSED = "processed"
        NEEDS_REVIEW = "needs_review"
        ERROR = "error"

    class Source(models.TextChoices):
        UPLOAD = "upload"
        GMAIL = "gmail"

    class Kind(models.TextChoices):
        SALE = "sale"
        RETURN = "return"

    # Source document
    pdf = models.FileField(upload_to=receipt_upload_path)
    pdf_sha256 = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.UPLOAD)
    gmail_message_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # Processing state
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    warnings = models.JSONField(default=list, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    # Parsed data
    invoice_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SALE)
    original_invoice_number = models.CharField(max_length=30, blank=True)
    store = models.ForeignKey(
        Store, on_delete=models.PROTECT, related_name="receipts", null=True, blank=True
    )
    issued_at = models.DateTimeField(null=True, blank=True, db_index=True)
    operation_number = models.CharField(max_length=20, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    vat_breakdown = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-issued_at", "-created_at"]

    def __str__(self) -> str:
        return self.invoice_number or f"Receipt #{self.pk} ({self.status})"


class ReceiptLine(models.Model):
    class LineType(models.TextChoices):
        PRODUCT = "product"
        DISCOUNT = "discount"
        RETURN = "return"
        OTHER = "other"

    class Unit(models.TextChoices):
        UNIT = "unit"
        KG = "kg"

    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveSmallIntegerField()
    line_type = models.CharField(max_length=20, choices=LineType.choices, default=LineType.PRODUCT)
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.UNIT)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Set from ProductAlias (FR-04); null while the description is unidentified
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_lines",
    )

    class Meta:
        ordering = ["receipt", "position"]
        constraints = [
            models.UniqueConstraint(fields=["receipt", "position"], name="unique_line_position")
        ]

    def __str__(self) -> str:
        return f"{self.quantity} {self.description} {self.amount}"
