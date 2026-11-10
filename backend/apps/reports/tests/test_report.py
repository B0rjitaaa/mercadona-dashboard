import base64
import email
from datetime import date, datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.models import JobRun
from apps.gmail_sync.client import GmailClient
from apps.receipts.models import Receipt, ReceiptLine
from apps.reports import report

pytestmark = pytest.mark.django_db
D = Decimal
TODAY = date(2026, 11, 9)  # Monday: the report covers 2-8 Nov


def receipt(n: int, day: str, lines: list[tuple[str, str]]) -> Receipt:
    total = sum((D(p) for _, p in lines), D("0"))
    r = Receipt.objects.create(
        pdf_sha256=f"{n:064d}",
        pdf="x.pdf",
        invoice_number=f"1-1-{n}",
        issued_at=timezone.make_aware(datetime.strptime(day, "%Y-%m-%d")),
        total=total,
        status=Receipt.Status.PROCESSED,
    )
    for i, (desc, price) in enumerate(lines, 1):
        ReceiptLine.objects.create(
            receipt=r,
            position=i,
            description=desc,
            quantity=1,
            unit_price=D(price),
            amount=D(price),
        )
    return r


@pytest.fixture
def data():
    receipt(1, "2026-10-20", [("LECHE", "8.00")])  # 4 weeks before: average 2.00/week
    receipt(2, "2026-11-03", [("LECHE", "1.20"), ("PAN", "0.80")])
    receipt(3, "2026-11-08", [("CAFÉ & TÉ", "3.00")])
    receipt(4, "2026-11-09", [("NOT THIS WEEK", "9.00")])


def test_build(data):
    d = report.build(TODAY)

    assert (d["period"].start, d["period"].end) == (date(2026, 11, 2), date(2026, 11, 8))
    assert (d["week"]["total"], d["week"]["receipts"]) == (D("5.00"), 2)
    assert d["average_week"] == D("2.00")
    assert d["month"]["total"] == D("5.00")  # 1-8 Nov
    assert [r["name"] for r in d["top"]] == ["CAFÉ & TÉ", "LECHE", "PAN"]
    assert d["unmatched"] == 4  # nothing linked to the catalogue in this test


def test_render_spanish(data):
    subject, text, html = report.render(report.build(TODAY), "es", "http://server:8080/")

    assert subject == "Mercadona · semana del 2 nov al 8 nov: 5,00 €"
    assert "Gasto de la semana: 5,00 € (2 tickets)" in text
    assert "+150,0 % frente a tu media de las 4 semanas anteriores (2,00 €)" in text
    assert "En lo que va de noviembre: 5,00 €" in text
    assert "4 productos nuevos sin identificar: http://server:8080/review" in text
    assert "CAFÉ &amp; TÉ" in html and "CAFÉ & TÉ" in text  # escaped only in HTML
    assert "http://server:8080/products/unidentified/CAF%C3%89%20%26%20T%C3%89" in html


def test_render_english_money():
    f = report.Formatter("en")
    assert (f.money(D("1234.5")), f.pct(D("-3.25")), f.day(date(2026, 1, 5))) == (
        "€1,234.50",
        "-3.2%",
        "Jan 5",
    )
    assert report.Formatter("es").money(D("-1234.5")) == "-1.234,50 €"


def test_mask():
    assert report.mask("someone@example.com") == "so…@example.com"


def test_send_skips_without_recipient(settings):
    settings.REPORT_EMAIL_TO = ""
    run = report.send_weekly(TODAY)
    assert run.status == JobRun.Status.SUCCESS and run.stats["sent"] == 0


def test_send_fails_without_send_scope(settings, monkeypatch):
    settings.REPORT_EMAIL_TO = "me@example.com"
    monkeypatch.setattr(report, "can_send", lambda: False)
    run = report.send_weekly(TODAY)
    assert run.status == JobRun.Status.FAILED and "gmail-auth" in run.error


class FakeService:
    def __init__(self):
        self.sent = []

    def users(self):
        return self

    def messages(self):
        return self

    def send(self, userId, body):
        self.sent.append(body)
        return self

    def execute(self):
        return {"id": "abc"}


def test_send(data, settings, monkeypatch):
    settings.REPORT_EMAIL_TO = "me@example.com"
    service = FakeService()
    monkeypatch.setattr(report, "can_send", lambda: True)
    monkeypatch.setattr(GmailClient, "from_token_file", classmethod(lambda cls, _: cls(service)))

    run = report.send_weekly(TODAY)

    assert run.status == JobRun.Status.SUCCESS and run.stats == {"sent": 1}
    message = email.message_from_bytes(base64.urlsafe_b64decode(service.sent[0]["raw"]))
    assert message["To"] == "me@example.com"
    assert message.get_content_type() == "multipart/alternative"


def test_status_and_preview(client, data, settings):
    settings.REPORT_EMAIL_TO = "someone@example.com"
    body = client.get(reverse("report-status")).json()
    assert body["recipient"] == "so…@example.com" and body["schedule"]["day"] == "mon"

    assert client.get(reverse("report-preview")).headers["Content-Type"].startswith("text/html")
    text = client.get(reverse("report-preview"), {"format": "text"}).content.decode()
    assert text.startswith("Mercadona ·")
