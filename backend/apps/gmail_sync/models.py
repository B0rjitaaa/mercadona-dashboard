from django.db import models

from apps.core.models import TimeStampedModel


class GmailMessage(TimeStampedModel):
    """Every Gmail message seen by the sync, so it is never processed twice (NFR-03)."""

    class Status(models.TextChoices):
        IMPORTED = "imported"  # at least one new receipt created
        DUPLICATE = "duplicate"  # only PDFs we already had
        NO_PDF = "no_pdf"
        ERROR = "error"

    message_id = models.CharField(max_length=64, unique=True)
    thread_id = models.CharField(max_length=64, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    pdf_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.subject or self.message_id} ({self.status})"
