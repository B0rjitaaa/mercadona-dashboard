from pathlib import Path

import pytest
from django.urls import reverse

from apps.core.models import JobRun
from apps.gmail_sync.client import Attachment, GmailNotAuthorisedError, Message
from apps.gmail_sync.models import GmailMessage
from apps.gmail_sync.services import sync_gmail
from apps.receipts.models import Receipt
from apps.receipts.tests.pdf_factory import build_receipt_pdf

pytestmark = pytest.mark.django_db

SAMPLE = (
    Path(__file__).parents[2] / "receipts" / "tests" / "fixtures" / "sample_receipt.txt"
).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolated_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def receipt_pdf(invoice: str) -> bytes:
    return build_receipt_pdf(SAMPLE.replace("1234-001-000001", invoice))


class FakeClient:
    def __init__(self, messages: dict[str, Message], failing: set[str] | None = None):
        self.messages = messages
        self.failing = failing or set()
        self.fetched: list[str] = []

    def list_message_ids(self, query):
        return list(self.messages)

    def get_message(self, message_id):
        self.fetched.append(message_id)
        if message_id in self.failing:
            raise ConnectionError("network down")
        return self.messages[message_id]


def message(message_id: str, *pdfs: bytes) -> Message:
    return Message(
        id=message_id,
        thread_id="t",
        received_at=None,
        sender="Me <me@example.com>",
        subject=f"Fwd: ticket {message_id}",
        attachments=[Attachment(f"{i}.pdf", pdf) for i, pdf in enumerate(pdfs)],
    )


def test_first_sync_imports_everything():
    client = FakeClient(
        {
            "m1": message("m1", receipt_pdf("1-1-1")),
            "m2": message("m2", receipt_pdf("2-2-2"), receipt_pdf("3-3-3")),
            "m3": message("m3"),
        }
    )

    run = sync_gmail(client)

    assert run.status == JobRun.Status.SUCCESS
    assert run.stats == {
        "messages_found": 3,
        "new_messages": 3,
        "receipts_created": 3,
        "duplicates": 0,
        "no_pdf": 1,
        "errors": 0,
    }
    assert Receipt.objects.filter(source="gmail", status="processed").count() == 3
    assert set(Receipt.objects.values_list("gmail_message_id", flat=True)) == {"m1", "m2"}
    assert GmailMessage.objects.get(message_id="m3").status == GmailMessage.Status.NO_PDF


def test_second_sync_only_fetches_new_messages():
    client = FakeClient({"m1": message("m1", receipt_pdf("1-1-1"))})
    sync_gmail(client)

    client.messages["m2"] = message("m2", receipt_pdf("2-2-2"))
    client.fetched.clear()
    run = sync_gmail(client)

    assert client.fetched == ["m2"]
    assert run.stats["new_messages"] == 1
    assert Receipt.objects.count() == 2


def test_same_pdf_in_two_emails_is_a_duplicate():
    pdf = receipt_pdf("1-1-1")
    run = sync_gmail(FakeClient({"m1": message("m1", pdf), "m2": message("m2", pdf)}))

    assert run.stats["receipts_created"] == 1
    assert run.stats["duplicates"] == 1
    assert GmailMessage.objects.get(message_id="m2").status == GmailMessage.Status.DUPLICATE


def test_failed_message_is_retried_next_time():
    client = FakeClient({"m1": message("m1", receipt_pdf("1-1-1"))}, failing={"m1"})
    run = sync_gmail(client)

    assert run.status == JobRun.Status.SUCCESS
    assert run.stats["errors"] == 1
    assert GmailMessage.objects.get(message_id="m1").status == GmailMessage.Status.ERROR

    client.failing.clear()
    run = sync_gmail(client)

    assert run.stats["receipts_created"] == 1
    assert GmailMessage.objects.get(message_id="m1").status == GmailMessage.Status.IMPORTED


def test_non_receipt_pdf_is_stored_as_error_receipt():
    run = sync_gmail(FakeClient({"m1": message("m1", build_receipt_pdf("Hello"))}))

    assert run.stats["receipts_created"] == 1
    assert Receipt.objects.get().status == Receipt.Status.ERROR


def test_not_authorised_marks_run_as_failed(monkeypatch):
    def raise_not_authorised(*args, **kwargs):
        raise GmailNotAuthorisedError("Token not found")

    monkeypatch.setattr(
        "apps.gmail_sync.services.GmailClient.from_token_file", raise_not_authorised
    )

    run = sync_gmail()

    assert run.status == JobRun.Status.FAILED
    assert "Token not found" in run.error


def test_status_and_jobs_endpoints(client, settings, tmp_path):
    settings.GMAIL_TOKEN_FILE = str(tmp_path / "missing.json")
    sync_gmail(FakeClient({}))

    status = client.get(reverse("gmail-status")).json()
    assert status["authorised"] is False
    assert status["last_run"]["status"] == "success"

    jobs = client.get(reverse("job-list"), {"job": "sync_gmail"}).json()
    assert jobs["count"] == 1
