from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.products.models import Product
from apps.receipts.models import Receipt, ReceiptLine

pytestmark = pytest.mark.django_db
D = Decimal
NOW = timezone.make_aware(datetime(2026, 11, 10, 12, 0))


@pytest.fixture(autouse=True)
def _frozen_now(monkeypatch):
    monkeypatch.setattr("apps.analytics.prices.timezone.now", lambda: NOW)
    monkeypatch.setattr("apps.analytics.prices.timezone.localdate", lambda: NOW.date())


_n = iter(range(1, 10_000))


def buy(product, days_ago, price, qty="1", unit="unit"):
    n = next(_n)
    r = Receipt.objects.create(
        pdf_sha256=f"{n:064d}",
        pdf="x.pdf",
        status="processed",
        issued_at=NOW - timedelta(days=days_ago),
    )
    ReceiptLine.objects.create(
        receipt=r,
        position=1,
        description=product.name.upper(),
        quantity=D(qty),
        unit=unit,
        unit_price=D(price),
        amount=(D(qty) * D(price)).quantize(D("0.01")),
        product=product,
    )


@pytest.fixture
def data():
    leche = Product.objects.create(mercadona_id="1", name="Leche", unit_price=D("1.10"))
    leche.catalog_prices.create(date=date(2026, 10, 1), unit_price=D("1.00"))
    leche.catalog_prices.create(date=date(2026, 11, 5), unit_price=D("1.10"))
    for days in (370, 60, 30, 10):  # paid 0.80 a year ago, 1.00 last time
        buy(leche, days, "0.80" if days > 300 else "1.00", qty="2")

    platano = Product.objects.create(
        mercadona_id="2", name="Plátano", unit_price=D("0.40"), bulk_price=D("2.90")
    )
    for days in (50, 20, 5):
        buy(platano, days, "3.20", qty="1.000", unit="kg")

    same = Product.objects.create(mercadona_id="3", name="Pan", unit_price=D("1.00"))
    for days in (40, 20, 2):
        buy(same, days, "1.00")

    rare = Product.objects.create(mercadona_id="4", name="Raro", unit_price=D("9.00"))
    buy(rare, 10, "5.00")  # bought once: not regular

    old = Product.objects.create(mercadona_id="5", name="Antiguo", unit_price=D("9.00"))
    for days in (400, 390, 380):  # not bought in the last 180 days
        buy(old, days, "5.00")

    # Variable-weight tray: never compared with the paid price, catalogue followed per kg
    tray = Product.objects.create(
        mercadona_id="6",
        name="Filetes pollo",
        unit_price=D("4.67"),
        bulk_price=D("8.20"),
        raw={"price_instructions": {"approx_size": True}},
    )
    tray.catalog_prices.create(date=date(2026, 10, 1), unit_price=D("4.50"), bulk_price=D("7.90"))
    tray.catalog_prices.create(date=date(2026, 11, 8), unit_price=D("4.67"), bulk_price=D("8.20"))
    for days in (30, 15, 3):
        buy(tray, days, "3.70")

    # Probably a wrong link: 4.50 paid, 2.20 in the catalogue
    wrong = Product.objects.create(mercadona_id="7", name="Pasta", unit_price=D("2.20"))
    for days in (30, 15, 3):
        buy(wrong, days, "4.50")
    return {"leche": leche, "platano": platano}


def test_price_watch(client, data):
    body = client.get(reverse("analytics-prices")).json()

    assert body["regular_products"] == 5
    names = [a["name"] for a in body["alerts"]]
    assert names == ["Plátano", "Leche"]  # sorted by yearly impact; "Pan" did not change

    platano, leche = body["alerts"]
    # Weighed product compares per-kg prices: 3.20 paid, 2.90 now, 3 kg in 12 months
    assert (platano["last_paid"], platano["catalog_price"], platano["diff_pct"]) == (
        "3.20",
        "2.90",
        "-9.4",
    )
    assert platano["impact_12m"] == "-0.90"
    assert (leche["diff"], leche["diff_pct"], leche["impact_12m"]) == ("0.10", "10.0", "0.60")
    assert (
        leche["catalog_previous"],
        leche["catalog_changed_at"],
        leche["catalog_change_pct"],
    ) == (
        "1.00",
        "2026-11-05",
        "10.0",
    )

    assert [r["name"] for r in body["check_links"]] == ["Pasta"]
    tray = next(r for r in body["recent_changes"] if r["name"] == "Filetes pollo")
    assert tray["variable_weight"] and tray["diff"] is None and tray["impact_12m"] is None
    assert (tray["catalog_price"], tray["catalog_previous"], tray["catalog_change_pct"]) == (
        "8.20",
        "7.90",
        "3.8",
    )
    assert [r["name"] for r in body["recent_changes"]] == ["Filetes pollo", "Leche"]
    summary = body["summary"]
    assert (summary["up"], summary["down"], summary["impact_12m"]) == (1, 1, "-0.30")
    # Only "Leche" was bought a year ago: 0.80 then, 1.10 now
    assert (summary["inflation_12m"], summary["inflation_products"]) == ("37.5", 1)


def test_recent_window(client, data):
    body = client.get(reverse("analytics-prices"), {"days": "3"}).json()

    # Only the tray changed in the last 3 days (2026-11-08); the milk changed on 11-05
    assert [r["name"] for r in body["recent_changes"]] == ["Filetes pollo"]
    assert client.get(reverse("analytics-prices"), {"days": "0"}).status_code == 400


def test_empty(client):
    body = client.get(reverse("analytics-prices")).json()

    assert body["alerts"] == [] and body["summary"]["inflation_12m"] is None
