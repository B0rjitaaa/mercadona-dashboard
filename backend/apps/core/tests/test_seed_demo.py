import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.products.models import Product
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_and_removes_fictitious_data():
    call_command("seed_demo", months=3)

    assert Receipt.objects.exists()
    assert not Receipt.objects.exclude(invoice_number__startswith="DEMO-").exists()
    assert Product.objects.filter(mercadona_id__startswith="DEMO-").exists()
    with pytest.raises(CommandError, match="already there"):
        call_command("seed_demo", months=3)

    call_command("seed_demo", remove=True)
    assert not Receipt.objects.exists()
    assert not Product.objects.exists()


def test_seed_demo_never_touches_real_receipts():
    Receipt.objects.create(
        pdf="x.pdf", pdf_sha256="0" * 64, invoice_number="1-1-1", issued_at=timezone.now()
    )

    for options in ({}, {"remove": True}, {"flush": True}):
        with pytest.raises(CommandError, match="real receipts"):
            call_command("seed_demo", **options)
    assert Receipt.objects.count() == 1
