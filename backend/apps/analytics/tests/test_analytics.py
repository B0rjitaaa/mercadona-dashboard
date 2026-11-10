import itertools
from datetime import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.receipts.models import Receipt, ReceiptLine

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture(autouse=True)
def _frozen_today(monkeypatch):
    monkeypatch.setattr(
        "apps.analytics.services.timezone.localdate", lambda: datetime(2026, 11, 10).date()
    )


_counter = itertools.count(1)


def receipt(day: str, lines: list[tuple[str, str, str]], status="processed") -> Receipt:
    """lines: (description, quantity, unit_price)."""
    n = next(_counter)
    issued = timezone.make_aware(datetime.strptime(day, "%Y-%m-%d %H:%M"))
    total = sum((D(q) * D(p) for _, q, p in lines), D("0")).quantize(D("0.01"))
    r = Receipt.objects.create(
        pdf_sha256=f"{n:064d}",
        pdf="x.pdf",
        invoice_number=f"1-1-{n}",
        issued_at=issued,
        total=total,
        status=status,
    )
    for i, (desc, qty, price) in enumerate(lines, 1):
        ReceiptLine.objects.create(
            receipt=r,
            position=i,
            description=desc,
            quantity=D(qty),
            unit_price=D(price),
            amount=(D(qty) * D(price)).quantize(D("0.01")),
        )
    return r


@pytest.fixture
def data():
    receipt("2026-09-05 10:00", [("LECHE", "1", "1.00"), ("PAN", "2", "0.50")])  # 2.00
    receipt("2026-11-01 10:00", [("LECHE", "1", "1.20")])  # 1.20
    receipt("2026-11-08 10:00", [("LECHE", "2", "1.25"), ("PAN", "1", "0.60")])  # 3.10
    receipt("2026-11-09 10:00", [("IGNORED", "1", "9.99")], status="error")


def test_monthly_is_contiguous_with_zero_months(client, data):
    rows = client.get(reverse("analytics-monthly"), {"months": "3"}).json()

    assert rows == [
        {"month": "2026-09", "total": "2.00", "receipts": 1, "average_receipt": "2.00"},
        {"month": "2026-10", "total": "0.00", "receipts": 0, "average_receipt": "0.00"},
        {"month": "2026-11", "total": "4.30", "receipts": 2, "average_receipt": "2.15"},
    ]


def test_monthly_all_starts_at_first_receipt(client, data):
    rows = client.get(reverse("analytics-monthly"), {"months": "all"}).json()

    assert [r["month"] for r in rows] == ["2026-09", "2026-10", "2026-11"]


def test_monthly_rejects_bad_param(client):
    assert client.get(reverse("analytics-monthly"), {"months": "x"}).status_code == 400


def test_summary(client, data):
    body = client.get(reverse("analytics-summary")).json()

    assert body["current_month"]["total"] == "4.30"
    assert body["previous_month"]["total"] == "0.00"
    assert body["average_month_12"] == "2.00"  # only months with receipts
    assert body["all_time"] == {"total": "6.30", "receipts": 3}
    assert body["pending"] == {"needs_review": 0, "error": 1}
    assert body["last_sync"] is None


def test_top_items(client, data):
    body = client.get(reverse("analytics-top-items"), {"month": "2026-11"}).json()

    top = body["by_spend"][0]
    assert (top["key"], top["name"], top["product_id"]) == ("d:LECHE", "LECHE", None)
    assert (top["spent"], top["purchases"], top["quantity"]) == ("3.70", 2, "3.000")
    assert [r["name"] for r in body["by_purchases"]] == ["LECHE", "PAN"]


def test_items_list_and_sorting(client, data):
    rows = client.get(reverse("analytics-items")).json()

    leche = rows[0]
    assert leche["name"] == "LECHE" and leche["key"] == "d:LECHE"
    assert leche["purchases"] == 3
    assert leche["spent"] == "4.70"
    assert leche["first_price"] == "1.00"
    assert leche["last_price"] == "1.25"
    assert leche["price_change_pct"] == "25.0"
    assert leche["trend"] == ["1.00", "1.20", "1.25"]

    by_name = client.get(reverse("analytics-items"), {"sort": "name"}).json()
    assert [r["name"] for r in by_name] == ["LECHE", "PAN"]
    assert len(client.get(reverse("analytics-items"), {"search": "pa"}).json()) == 1


def test_item_detail(client, data):
    body = client.get(reverse("analytics-item-detail"), {"description": "LECHE"}).json()

    assert body["purchases"] == 3
    assert body["average_price"] == "1.15"
    assert body["frequency_days"] == 32  # 2026-09-05 -> 11-01 -> 11-08
    assert [h["unit_price"] for h in body["history"]] == ["1.00", "1.20", "1.25"]
    assert body["monthly"] == [
        {"month": "2026-09", "spent": "1.00", "quantity": "1.000"},
        {"month": "2026-11", "spent": "3.70", "quantity": "3.000"},
    ]


def test_item_detail_not_found(client):
    response = client.get(reverse("analytics-item-detail"), {"description": "NOPE"})

    assert response.status_code == 404


@pytest.fixture
def linked(data):
    from apps.products.models import Category, Product
    from apps.products.services import link

    section = Category.objects.create(id=1, name="Lácteos", level=0)
    cat = Category.objects.create(id=10, name="Leche", level=1, parent=section)
    sub = Category.objects.create(id=100, name="Leche desnatada", level=2, parent=cat)
    product = Product.objects.create(
        mercadona_id="1", name="Leche desnatada Hacendado", category=sub, unit_price=D("1.30")
    )
    product.catalog_prices.create(date=datetime(2026, 11, 1).date(), unit_price=D("1.30"))
    # Two receipt descriptions for the same product are merged
    ReceiptLine.objects.filter(description="PAN").update(description="LECHE DESN")
    link("LECHE", product, "manual")
    link("LECHE DESN", product, "auto", D("0.9"))
    return product


def test_items_are_grouped_by_product(client, linked):
    rows = client.get(reverse("analytics-items")).json()

    assert len(rows) == 1
    row = rows[0]
    assert (row["key"], row["product_id"], row["name"], row["section"]) == (
        f"p{linked.pk}",
        linked.pk,
        "Leche desnatada Hacendado",
        "Lácteos",
    )
    assert row["purchases"] == 3
    assert row["spent"] == "6.30"


def test_product_detail(client, linked):
    body = client.get(reverse("analytics-product-detail", args=[linked.pk])).json()

    assert body["product"]["category_path"] == ["Lácteos", "Leche", "Leche desnatada"]
    assert {a["description"] for a in body["aliases"]} == {"LECHE", "LECHE DESN"}
    assert body["catalog_prices"] == [{"date": "2026-11-01", "price": "1.30"}]
    assert body["history"][0]["description"] in {"LECHE", "LECHE DESN"}
    assert client.get(reverse("analytics-product-detail", args=[999])).status_code == 404


def test_categories(client, linked):
    receipt("2026-11-09 12:00", [("SIN ENLAZAR", "1", "2.00")])

    body = client.get(reverse("analytics-categories"), {"month": "2026-11"}).json()

    assert body["total"] == "6.30"
    assert [(s["section"], s["spent"], s["share"]) for s in body["sections"]] == [
        ("Lácteos", "4.30", "68.3"),
        (None, "2.00", "31.7"),
    ]
