from decimal import Decimal

import pytest
from django.urls import reverse

from apps.products.models import MatchSuggestion, Product, ProductAlias
from apps.products.services import match_descriptions
from apps.receipts.models import Receipt, ReceiptLine

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture(autouse=True)
def _eager(settings):
    from config.celery import app

    app.conf.task_always_eager = True
    yield
    app.conf.task_always_eager = False


@pytest.fixture
def catalog():
    return {
        "leche": Product.objects.create(
            mercadona_id="1",
            name="Leche desnatada Hacendado",
            packaging="Pack-6",
            unit_price=D("4.86"),
        ),
        "zero": Product.objects.create(
            mercadona_id="2", name="Refresco Coca-Cola zero azúcar", unit_price=D("4.18")
        ),
        "zero0": Product.objects.create(
            mercadona_id="3",
            name="Refresco Coca-Cola zero azúcar zero cafeína",
            unit_price=D("4.18"),
        ),
    }


@pytest.fixture
def receipt():
    r = Receipt.objects.create(
        pdf_sha256="a" * 64, pdf="x.pdf", status="processed", total=D("13.22")
    )
    for i, (desc, price) in enumerate(
        [
            ("LECHE DESN P6", "4.86"),
            ("COLA ZERO ZERO", "4.18"),
            ("COLA ZERO ZERO", "4.18"),
            ("RARO", "1.00"),
        ],
        1,
    ):
        ReceiptLine.objects.create(
            receipt=r,
            position=i,
            description=desc,
            quantity=1,
            unit_price=D(price),
            amount=D(price),
        )
    return r


def test_matching_auto_links_and_suggests(catalog, receipt):
    run = match_descriptions()

    assert run.stats == {"checked": 3, "auto_linked": 1, "suggested": 1, "no_candidates": 1}
    assert ProductAlias.objects.get(description="LECHE DESN P6").product == catalog["leche"]
    assert receipt.lines.get(description="LECHE DESN P6").product == catalog["leche"]
    assert MatchSuggestion.objects.filter(description="COLA ZERO ZERO").count() == 2


def test_matching_without_catalogue_does_nothing(receipt):
    run = match_descriptions()

    assert "Catalogue is empty" in run.error
    assert not ProductAlias.objects.exists()


def test_review_list_and_manual_link(client, catalog, receipt):
    match_descriptions()

    rows = client.get(reverse("review-list")).json()
    assert [r["description"] for r in rows] == ["COLA ZERO ZERO", "RARO"]  # by spend
    assert rows[0]["purchases"] == 1 and rows[0]["spent"] == "8.36"
    assert len(rows[0]["suggestions"]) == 2

    response = client.post(
        reverse("review-link"), {"description": "COLA ZERO ZERO", "product_id": catalog["zero0"].pk}
    )
    assert response.status_code == 200
    assert receipt.lines.filter(product=catalog["zero0"]).count() == 2
    assert ProductAlias.objects.get(description="COLA ZERO ZERO").source == "manual"
    assert not MatchSuggestion.objects.filter(description="COLA ZERO ZERO").exists()


def test_manual_product(client, catalog, receipt):
    response = client.post(
        reverse("review-manual"), {"description": "RARO", "name": "Producto raro"}
    )

    assert response.status_code == 201
    product = Product.objects.get(pk=response.json()["id"])
    assert product.is_manual and product.name == "Producto raro"
    assert receipt.lines.get(description="RARO").product == product


def test_unlink_clears_lines_and_queues_rematch(client, catalog, receipt, monkeypatch):
    match_descriptions()
    queued = []
    monkeypatch.setattr("apps.products.views.match_products_task.delay", queued.append)

    response = client.post(reverse("review-unlink"), {"description": "LECHE DESN P6"})

    assert response.status_code == 204
    assert receipt.lines.get(description="LECHE DESN P6").product is None
    assert not ProductAlias.objects.filter(description="LECHE DESN P6").exists()
    assert queued == [["LECHE DESN P6"]]


def test_new_receipt_uses_existing_alias(catalog, receipt):
    from apps.products.services import apply_aliases

    ProductAlias.objects.create(description="RARO", product=catalog["leche"], source="manual")

    apply_aliases(receipt)

    assert receipt.lines.get(description="RARO").product == catalog["leche"]


def test_catalog_search_and_status(client, catalog, receipt):
    match_descriptions()

    found = client.get(reverse("catalog-search"), {"q": "coca cola zero"}).json()
    assert {p["mercadona_id"] for p in found[:2]} == {"2", "3"}
    assert client.get(reverse("catalog-search"), {"q": "x"}).json() == []

    status = client.get(reverse("catalog-status")).json()
    assert status["products"] == 3 and status["aliases"] == 1 and status["unmatched"] == 2
