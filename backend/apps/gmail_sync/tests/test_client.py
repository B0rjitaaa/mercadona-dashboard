import base64

from apps.gmail_sync.client import GmailClient, iter_pdf_parts


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


FORWARDED_PAYLOAD = {
    "mimeType": "multipart/mixed",
    "headers": [
        {"name": "From", "value": "Me <me@example.com>"},
        {"name": "Subject", "value": "Fwd: Ticket Mercadona"},
    ],
    "parts": [
        {
            "mimeType": "multipart/alternative",
            "filename": "",
            "parts": [{"mimeType": "text/plain", "filename": "", "body": {"data": b64(b"hi")}}],
        },
        {
            "mimeType": "application/pdf",
            "filename": "receipt 43,55 €.pdf",
            "body": {"attachmentId": "att-1"},
        },
        {"mimeType": "image/png", "filename": "logo.png", "body": {"attachmentId": "att-2"}},
        {
            "mimeType": "application/octet-stream",
            "filename": "TICKET.PDF",
            "body": {"data": b64(b"%PDF-inline")},
        },
    ],
}


def test_iter_pdf_parts_finds_nested_pdfs_only():
    names = [part["filename"] for part in iter_pdf_parts(FORWARDED_PAYLOAD)]

    assert names == ["receipt 43,55 €.pdf", "TICKET.PDF"]


class FakeRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeMessages:
    """Mimics service.users().messages() with two pages of results."""

    def __init__(self):
        self.pages = [
            {"messages": [{"id": "m3"}, {"id": "m2"}], "nextPageToken": "p2"},
            {"messages": [{"id": "m1"}]},
        ]

    def list(self, **kwargs):
        return FakeRequest(self.pages[0])

    def list_next(self, request, response):
        return FakeRequest(self.pages[1]) if response.get("nextPageToken") else None

    def get(self, userId, id, format):
        return FakeRequest(
            {
                "id": id,
                "threadId": "t1",
                "internalDate": "1762347720000",
                "payload": FORWARDED_PAYLOAD,
            }
        )

    def attachments(self):
        return self

    def get_attachment(self, **kwargs):  # pragma: no cover - replaced below
        raise NotImplementedError


class FakeAttachments:
    def get(self, userId, messageId, id):
        return FakeRequest({"data": b64(b"%PDF-from-attachment")})


class FakeService:
    def __init__(self):
        self._messages = FakeMessages()
        self._messages.attachments = lambda: FakeAttachments()

    def users(self):
        return self

    def messages(self):
        return self._messages


def test_list_message_ids_paginates_oldest_first():
    assert GmailClient(FakeService()).list_message_ids("q") == ["m1", "m2", "m3"]


def test_get_message_downloads_attachments():
    message = GmailClient(FakeService()).get_message("m1")

    assert message.subject == "Fwd: Ticket Mercadona"
    assert message.sender == "Me <me@example.com>"
    assert message.received_at.isoformat() == "2025-11-05T13:02:00+00:00"
    assert [(a.filename, a.content) for a in message.attachments] == [
        ("receipt 43,55 €.pdf", b"%PDF-from-attachment"),
        ("TICKET.PDF", b"%PDF-inline"),
    ]
