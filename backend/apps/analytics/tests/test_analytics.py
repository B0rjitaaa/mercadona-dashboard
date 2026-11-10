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


# --- Dynamic filters (FR-14) -------------------------------------------------


def test_previous_period():
    from datetime import date

    from apps.analytics.filters import Period

    today = date(2026, 11, 10)
    # Month-aligned periods shift by whole months, clipped to the month length
    assert Period(date(2026, 11, 1), None).previous(today) == Period(
        date(2026, 10, 1), date(2026, 10, 10)
    )
    assert Period(date(2026, 3, 1), date(2026, 3, 31)).previous(today) == Period(
        date(2026, 2, 1), date(2026, 2, 28)
    )
    assert Period(date(2025, 12, 1), date(2026, 11, 10)).previous(today) == Period(
        date(2024, 12, 1), date(2025, 11, 10)
    )
    # Other periods shift by their length in days
    assert Period(date(2026, 11, 5), date(2026, 11, 9)).previous(today) == Period(
        date(2026, 10, 31), date(2026, 11, 4)
    )
    assert Period().previous(today) is None


@pytest.mark.parametrize(
    "params",
    [{"from": "2026-13-01"}, {"from": "2026-11-05", "to": "2026-11-01"}, {"sections": "x"}],
)
def test_bad_filters_are_rejected(client, params):
    assert client.get(reverse("analytics-overview"), params).status_code == 400


def test_monthly_with_period(client, data):
    rows = client.get(
        reverse("analytics-monthly"), {"from": "2026-09-01", "to": "2026-10-31"}
    ).json()

    assert [(r["month"], r["total"]) for r in rows] == [("2026-09", "2.00"), ("2026-10", "0.00")]


def test_monthly_with_section_sums_matching_lines(client, linked):
    receipt("2026-11-09 12:00", [("SIN ENLAZAR", "1", "2.00")])

    rows = client.get(reverse("analytics-monthly"), {"months": "3", "sections": "1"}).json()
    assert [(r["month"], r["total"], r["receipts"]) for r in rows] == [
        ("2026-09", "2.00", 1),
        ("2026-10", "0.00", 0),
        ("2026-11", "4.30", 2),
    ]
    rows = client.get(reverse("analytics-monthly"), {"months": "1", "sections": "none"}).json()
    assert [(r["month"], r["total"]) for r in rows] == [("2026-11", "2.00")]


def test_overview(client, data):
    body = client.get(
        reverse("analytics-overview"), {"from": "2026-11-01", "to": "2026-11-30"}
    ).json()

    assert (body["total"], body["receipts"], body["average_receipt"]) == ("4.30", 2, "2.15")
    assert (body["months"], body["average_month"]) == (1, "4.30")
    assert body["previous"]["from"] == "2026-10-01" and body["previous"]["total"] == "0.00"
    assert [(i["name"], i["spent"]) for i in body["by_spend"]] == [
        ("LECHE", "3.70"),
        ("PAN", "0.60"),
    ]
    assert body["sections"] == [
        {"id": None, "section": None, "spent": "4.30", "share": "100.0", "items": 3}
    ]


def test_overview_all_time_has_no_previous(client, data):
    body = client.get(reverse("analytics-overview")).json()

    assert body["total"] == "6.30" and body["previous"] is None
    assert body["months"] == 3  # September to November


def test_categories_include_section_ids(client, linked):
    body = client.get(reverse("analytics-categories")).json()

    assert [(s["id"], s["section"]) for s in body["sections"]] == [(1, "Lácteos")]


def test_compare(client, data):
    body = client.get(
        reverse("analytics-compare"),
        {
            "a_from": "2026-11-01",
            "a_to": "2026-11-30",
            "b_from": "2026-09-01",
            "b_to": "2026-09-30",
        },
    ).json()

    assert (body["a"]["total"], body["b"]["total"], body["diff"], body["diff_pct"]) == (
        "4.30",
        "2.00",
        "2.30",
        "115.0",
    )
    leche = body["increases"][0]
    assert (leche["name"], leche["a_spent"], leche["b_spent"], leche["diff"]) == (
        "LECHE",
        "3.70",
        "1.00",
        "2.70",
    )
    # 3 units at 1.2333 instead of 1 at 1.00: price +0.70, quantity +2.00
    assert (leche["price_effect"], leche["quantity_effect"]) == ("0.70", "2.00")
    pan = body["decreases"][0]
    assert (pan["name"], pan["diff"]) == ("PAN", "-0.40")
    assert (body["new_items"], body["dropped_items"]) == (0, 0)


def test_compare_requires_both_periods(client):
    assert client.get(reverse("analytics-compare"), {"a_from": "2026-11-01"}).status_code == 400


def test_items_filters(client, data):
    url = reverse("analytics-items")

    in_nov = client.get(url, {"from": "2026-11-01"}).json()
    assert {(r["name"], r["purchases"]) for r in in_nov} == {("LECHE", 2), ("PAN", 1)}
    assert [r["name"] for r in client.get(url, {"min_purchases": "3"}).json()] == ["LECHE"]
    assert [r["name"] for r in client.get(url, {"trend": "up"}).json()] == ["LECHE", "PAN"]
    assert client.get(url, {"trend": "down"}).json() == []
    assert client.get(url, {"status": "identified"}).json() == []
    assert client.get(url, {"status": "bogus"}).status_code == 400


def test_items_section_filter(client, linked):
    receipt("2026-11-09 12:00", [("SIN ENLAZAR", "1", "2.00")])
    url = reverse("analytics-items")

    assert [r["name"] for r in client.get(url, {"sections": "1"}).json()] == [
        "Leche desnatada Hacendado"
    ]
    assert [r["name"] for r in client.get(url, {"sections": "none"}).json()] == ["SIN ENLAZAR"]
    assert client.get(url, {"status": "unidentified"}).json()[0]["name"] == "SIN ENLAZAR"
