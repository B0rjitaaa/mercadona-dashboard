import io
import logging

from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.core.models import JobRun
from apps.receipts.models import Receipt
from apps.receipts.services import DuplicateReceiptError, create_receipt, process_receipt

from .client import GmailClient
from .models import GmailMessage

logger = logging.getLogger(__name__)

JOB_NAME = "sync_gmail"
LOCK_ID = 846_101  # arbitrary Postgres advisory lock key for this job


class SyncAlreadyRunningError(Exception):
    pass


def sync_gmail(client: GmailClient | None = None, query: str | None = None) -> JobRun:
    """Import every new receipt from Gmail (FR-01).

    Lists all messages matching the query and skips the ones already seen, so the
    first run is a full historical import and later runs only fetch new emails.
    Messages that failed to download are retried on the next run.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
        if not cursor.fetchone()[0]:
            raise SyncAlreadyRunningError("A Gmail sync is already running")
    try:
        return _run(client, query)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])


def _run(client: GmailClient | None, query: str | None) -> JobRun:
    run = JobRun.objects.create(job=JOB_NAME)
    stats = {
        "messages_found": 0,
        "new_messages": 0,
        "receipts_created": 0,
        "duplicates": 0,
        "no_pdf": 0,
        "errors": 0,
    }
    try:
        client = client or GmailClient.from_token_file(settings.GMAIL_TOKEN_FILE)
        ids = client.list_message_ids(query or settings.GMAIL_QUERY)
        stats["messages_found"] = len(ids)

        known = set(
            GmailMessage.objects.filter(message_id__in=ids)
            .exclude(status=GmailMessage.Status.ERROR)
            .values_list("message_id", flat=True)
        )
        for message_id in ids:
            if message_id in known:
                continue
            stats["new_messages"] += 1
            _import_message(client, message_id, stats)

        run.status = JobRun.Status.SUCCESS
    except Exception as exc:
        logger.exception("Gmail sync failed")
        run.status = JobRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
    finally:
        run.stats = stats
        run.finished_at = timezone.now()
        run.save()
    return run


def _import_message(client: GmailClient, message_id: str, stats: dict) -> None:
    try:
        message = client.get_message(message_id)
    except Exception as exc:
        logger.exception("Cannot fetch Gmail message %s", message_id)
        stats["errors"] += 1
        GmailMessage.objects.update_or_create(
            message_id=message_id,
            defaults={"status": GmailMessage.Status.ERROR, "error": str(exc)},
        )
        return

    created = duplicates = 0
    for attachment in message.attachments:
        try:
            receipt = create_receipt(
                io.BytesIO(attachment.content),
                source=Receipt.Source.GMAIL,
                gmail_message_id=message.id,
            )
        except DuplicateReceiptError:
            duplicates += 1
            continue
        process_receipt(receipt)
        created += 1

    stats["receipts_created"] += created
    stats["duplicates"] += duplicates
    if not message.attachments:
        status = GmailMessage.Status.NO_PDF
        stats["no_pdf"] += 1
    elif created:
        status = GmailMessage.Status.IMPORTED
    else:
        status = GmailMessage.Status.DUPLICATE

    GmailMessage.objects.update_or_create(
        message_id=message.id,
        defaults={
            "thread_id": message.thread_id,
            "received_at": message.received_at,
            "sender": message.sender[:255],
            "subject": message.subject[:500],
            "pdf_count": len(message.attachments),
            "status": status,
            "error": "",
        },
    )
