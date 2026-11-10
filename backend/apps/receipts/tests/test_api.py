import os
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.receipts.models import Receipt, Store

from .pdf_factory import build_receipt_pdf

pytestmark = pytest.mark.django_db


def upload(client, content: bytes, name: str = "receipt.pdf"):
    file = SimpleUploadedFile(name, content, content_type="application/pdf")
    return client.post(reverse("receipt-upload"), {"file": file}, format="multipart")


def test_upload_parses_receipt(client, sample_pdf):
    response = upload(client, sample_pdf)

    assert response.status_code == 201
    receipt = Receipt.objects.get(pk=response.json()["id"])
    assert receipt.status == Receipt.Status.PROCESSED
    assert receipt.invoice_number == "1234-001-000001"
    assert receipt.total == Decimal("43.55")
    assert receipt.lines.count() == 14
    assert receipt.issued_at.isoformat() == "2026-01-15T09:30:00+00:00"  # 10:30 Madrid
    assert receipt.store.address == "CALLE EJEMPLO, 1"


def test_upload_same_pdf_twice_returns_conflict(client, sample_pdf):
    first = upload(client, sample_pdf).json()
    response = upload(client, sample_pdf)

    assert response.status_code == 409
    assert response.json()["id"] == first["id"]
    assert Receipt.objects.count() == 1


def test_same_invoice_in_different_pdf_is_flagged(client, sample_text):
    upload(client, build_receipt_pdf(sample_text))
    response = upload(client, build_receipt_pdf(sample_text + "\n"))  # different bytes

    receipt = Receipt.objects.get(pk=response.json()["id"])
    assert receipt.status == Receipt.Status.ERROR
    assert "Duplicate" in receipt.error_message
    assert Store.objects.count() == 1


def test_totals_mismatch_needs_review(client, sample_text):
    pdf = build_receipt_pdf(sample_text.replace("TOTAL (€) 43,55", "TOTAL (€) 44,00"))
    receipt = Receipt.objects.get(pk=upload(client, pdf).json()["id"])

    assert receipt.status == Receipt.Status.NEEDS_REVIEW
    assert "Lines add up to 43.55" in receipt.warnings[-1]


def test_unparseable_pdf_is_error(client):
    pdf = build_receipt_pdf("Just some random document")
    receipt = Receipt.objects.get(pk=upload(client, pdf).json()["id"])

    assert receipt.status == Receipt.Status.ERROR
    assert receipt.pdf  # original PDF kept for retry


def test_upload_rejects_non_pdf(client):
    response = upload(client, b"hello", name="notes.txt")

    assert response.status_code == 400


def test_list_detail_and_filters(client, sample_pdf):
    receipt_id = upload(client, sample_pdf).json()["id"]

    listing = client.get(reverse("receipt-list")).json()
    assert listing["count"] == 1
    assert listing["results"][0]["line_count"] == 14

    detail = client.get(reverse("receipt-detail", args=[receipt_id])).json()
    assert detail["lines"][-1] == {
        "id": detail["lines"][-1]["id"],
        "position": 14,
        "line_type": "product",
        "description": "PLATANO",
        "quantity": "0.728",
        "unit": "kg",
        "unit_price": "3.20",
        "amount": "2.33",
    }

    def count(**params):
        return client.get(reverse("receipt-list"), params).json()["count"]

    assert count(search="salmorejo") == 1
    assert count(search="pizza") == 0
    assert count(status="processed") == 1
    assert count(status="error") == 0
    assert count(date_from="2026-01-15", date_to="2026-01-15") == 1
    assert count(date_from="2026-01-16") == 0


def test_reprocess_is_idempotent(client, sample_pdf):
    receipt_id = upload(client, sample_pdf).json()["id"]

    response = client.post(reverse("receipt-reprocess", args=[receipt_id]))

    assert response.status_code == 202
    receipt = Receipt.objects.get(pk=receipt_id)
    assert receipt.status == Receipt.Status.PROCESSED
    assert receipt.lines.count() == 14


def test_delete_removes_pdf(client, sample_pdf):
    receipt_id = upload(client, sample_pdf).json()["id"]
    path = Receipt.objects.get(pk=receipt_id).pdf.path

    response = client.delete(reverse("receipt-detail", args=[receipt_id]))

    assert response.status_code == 204
    assert not Receipt.objects.exists()
    assert not os.path.exists(path)


def test_store_is_identified_by_code_not_address(client, sample_text):
    upload(client, build_receipt_pdf(sample_text))
    other_address = (
        sample_text.replace("1234-001-000001", "1234-009-000009")
        .replace("CALLE EJEMPLO, 1", "C/ EJEMPLO, 1")
        .replace("28001 MADRID", "28001 Madrid")
    )
    upload(client, build_receipt_pdf(other_address))

    store = Store.objects.get()
    assert store.code == "1234"
    assert store.city == "MADRID"
    assert store.receipts.count() == 2


def test_reprocess_command(client, sample_pdf):
    from django.core.management import call_command

    receipt_id = upload(client, sample_pdf).json()["id"]
    Receipt.objects.filter(pk=receipt_id).update(status=Receipt.Status.ERROR)

    call_command("reprocess_receipts", status="error")

    assert Receipt.objects.get(pk=receipt_id).status == Receipt.Status.PROCESSED
