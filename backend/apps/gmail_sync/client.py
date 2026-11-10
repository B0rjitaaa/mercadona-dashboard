"""Thin wrapper around the Gmail API (read-only)."""

import base64
import email
import quopri
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email import policy
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailNotAuthorisedError(Exception):
    """No valid OAuth token. Run `make gmail-auth`."""


@dataclass
class Attachment:
    filename: str
    content: bytes


@dataclass
class Message:
    id: str
    thread_id: str
    received_at: datetime | None
    sender: str
    subject: str
    attachments: list[Attachment] = field(default_factory=list)


def load_credentials(token_file: str | Path) -> Credentials:
    path = Path(token_file)
    if not path.exists():
        raise GmailNotAuthorisedError(f"Token not found at {path}. Run `make gmail-auth`.")
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if not creds.valid:
        if not (creds.expired and creds.refresh_token):
            raise GmailNotAuthorisedError("Token is invalid. Run `make gmail-auth` again.")
        creds.refresh(Request())
        path.write_text(creds.to_json())
    return creds


def _is_pdf(filename: str, mime: str) -> bool:
    return filename.lower().endswith(".pdf") or mime == "application/pdf"


def _is_email(filename: str, mime: str) -> bool:
    return mime == "message/rfc822" or filename.lower().endswith(".eml")


def iter_attachment_parts(payload: dict) -> Iterator[tuple[str, dict]]:
    """Yield ("pdf" | "eml", part) for every relevant attachment, however deeply nested.

    Receipts can arrive as a PDF attachment (direct or forwarded email) or inside an
    attached email (.eml) when forwarded "as attachment". Gmail sometimes expands the
    parts of an attached email and sometimes only gives the raw .eml: when the .eml is
    downloadable as a whole we take it and do not descend into it, to avoid counting
    its PDFs twice.
    """
    filename = payload.get("filename") or ""
    mime = payload.get("mimeType", "")
    has_body = bool(
        payload.get("body", {}).get("attachmentId") or payload.get("body", {}).get("data")
    )

    if _is_email(filename, mime) and has_body:
        yield "eml", payload
        return
    if filename and _is_pdf(filename, mime):
        yield "pdf", payload
        return
    for part in payload.get("parts", []) or []:
        yield from iter_attachment_parts(part)


def iter_pdf_parts(payload: dict) -> Iterator[dict]:
    """Yield the PDF parts of a payload (attached emails excluded)."""
    for kind, part in iter_attachment_parts(payload):
        if kind == "pdf":
            yield part


def pdfs_from_eml(raw: bytes) -> list[Attachment]:
    """Extract every PDF from a raw email (.eml), including emails attached inside it."""
    return list(_pdfs_in_part(email.message_from_bytes(raw, policy=policy.default)))


def _pdfs_in_part(part) -> Iterator[Attachment]:
    filename = part.get_filename() or ""
    ctype = part.get_content_type()

    if _is_email(filename, ctype) and part.get_content_maintype() != "multipart":
        encoding = (part.get("Content-Transfer-Encoding") or "").lower()
        if encoding in ("base64", "quoted-printable"):
            # The parser cannot see through an encoded attached email: decode it ourselves.
            payload = part.get_payload()
            encoded = payload[0].get_payload() if isinstance(payload, list) else payload
            raw = (
                base64.b64decode(encoded)
                if encoding == "base64"
                else quopri.decodestring(encoded.encode())
            )
            yield from pdfs_from_eml(raw)
            return

    if part.is_multipart():
        for sub in part.get_payload():
            yield from _pdfs_in_part(sub)
    elif _is_pdf(filename, ctype) and (content := part.get_payload(decode=True)):
        yield Attachment(filename=filename or "receipt.pdf", content=content)


def _header(payload: dict, name: str) -> str:
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class GmailClient:
    def __init__(self, service):
        self.service = service

    @classmethod
    def from_token_file(cls, token_file: str | Path) -> "GmailClient":
        creds = load_credentials(token_file)
        return cls(build("gmail", "v1", credentials=creds, cache_discovery=False))

    def list_message_ids(self, query: str) -> list[str]:
        """All message IDs matching the query (oldest first)."""
        ids: list[str] = []
        request = self.service.users().messages().list(userId="me", q=query, maxResults=500)
        while request is not None:
            response = request.execute()
            ids.extend(m["id"] for m in response.get("messages", []))
            request = self.service.users().messages().list_next(request, response)
        return list(reversed(ids))

    def get_message(self, message_id: str) -> Message:
        raw = (
            self.service.users().messages().get(userId="me", id=message_id, format="full").execute()
        )
        payload = raw.get("payload", {})
        internal_date = raw.get("internalDate")

        attachments: list[Attachment] = []
        for kind, part in iter_attachment_parts(payload):
            content = self._part_content(message_id, part)
            if content is None:
                continue
            if kind == "eml":
                attachments.extend(pdfs_from_eml(content))
            else:
                attachments.append(Attachment(filename=part["filename"], content=content))

        return Message(
            id=raw["id"],
            thread_id=raw.get("threadId", ""),
            received_at=(
                datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC) if internal_date else None
            ),
            sender=_header(payload, "From"),
            subject=_header(payload, "Subject"),
            attachments=attachments,
        )

    def _part_content(self, message_id: str, part: dict) -> bytes | None:
        body = part.get("body", {})
        if data := body.get("data"):
            return _decode(data)
        if attachment_id := body.get("attachmentId"):
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            return _decode(attachment["data"])
        return None
