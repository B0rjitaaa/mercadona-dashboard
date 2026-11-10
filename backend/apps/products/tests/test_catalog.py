from datetime import date

import pytest

from apps.core.models import JobRun
from apps.mercadona.client import CatalogEntry, MercadonaClient, MercadonaError
from apps.products.catalog import sync_catalog
from apps.products.models import CatalogPrice, Category, Product

pytestmark = pytest.mark.django_db

SECTION = {"id": 1, "name": "Lácteos", "order": 1}
CATEGORY = {"id": 10, "name": "Leche", "order": 1}
SUB = {"id": 100, "name": "Leche desnatada", "order": 1}


def product(pid: str, price: str, name="Leche desnatada Hacendado") -> dict:
    return {
        "id": pid,
        "display_name": name,
        "packaging": "Pack-6",
        "thumbnail": "https://example.com/x.jpg",
        "share_url": f"https://tienda.mercadona.es/product/{pid}/x",
        "price_instructions": {
            "unit_price": price,
            "bulk_price": "0.81",
            "reference_price": "0.810",
            "reference_format": "L",
            "size_format": "l",
            "unit_size": 6,
        },
    }


class FakeClient:
    def __init__(self, products, errors=()):
        self.products = products
        self.errors = list(errors)

    def iter_catalog(self, errors=None):
        errors.extend(self.errors)
        for p in self.products:
            yield CatalogEntry(p, SECTION, CATEGORY, SUB)


def test_first_sync_creates_categories_products_and_prices():
    run = sync_catalog(FakeClient([product("1", "4.86"), product("2", "1.00", "Otra")]))

    assert run.status == JobRun.Status.SUCCESS
    assert run.stats["products_new"] == 2
    assert Category.objects.get(id=100).parent.parent.name == "Lácteos"
    leche = Product.objects.get(mercadona_id="1")
    assert leche.category.name == "Leche desnatada"
    assert str(leche.unit_price) == "4.86"
    assert CatalogPrice.objects.filter(product=leche).count() == 1


def test_price_change_adds_history_row(monkeypatch):
    sync_catalog(FakeClient([product("1", "4.86")]))
    monkeypatch.setattr("apps.products.catalog.timezone.localdate", lambda: date(2030, 1, 1))

    run = sync_catalog(FakeClient([product("1", "4.99")]))

    assert run.stats["price_changes"] == 1
    prices = list(CatalogPrice.objects.values_list("unit_price", flat=True))
    assert [str(p) for p in prices] == ["4.86", "4.99"]


def test_same_price_adds_no_row(monkeypatch):
    sync_catalog(FakeClient([product("1", "4.86")]))
    monkeypatch.setattr("apps.products.catalog.timezone.localdate", lambda: date(2030, 1, 1))
    sync_catalog(FakeClient([product("1", "4.86")]))

    assert CatalogPrice.objects.count() == 1


def test_missing_products_are_discontinued_only_after_complete_sync():
    sync_catalog(FakeClient([product("1", "4.86"), product("2", "1.00")]))

    sync_catalog(FakeClient([product("1", "4.86")], errors=["GET categories/10/ failed"]))
    assert Product.objects.get(mercadona_id="2").is_active  # incomplete: keep it

    run = sync_catalog(FakeClient([product("1", "4.86")]))
    assert run.stats["discontinued"] == 1
    assert not Product.objects.get(mercadona_id="2").is_active


def test_client_error_marks_run_failed():
    class Broken:
        def iter_catalog(self, errors=None):
            raise MercadonaError("GET categories/ failed")
            yield  # pragma: no cover

    run = sync_catalog(Broken())

    assert run.status == JobRun.Status.FAILED
    assert "categories/" in run.error


def test_client_iterates_categories(settings):
    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    class Session:
        def get(self, url, params, timeout):
            assert params == {"lang": "es", "wh": "svq1"}
            if url.endswith("/categories/"):
                return Response({"results": [{**SECTION, "categories": [CATEGORY]}]})
            return Response(
                {**CATEGORY, "categories": [{**SUB, "products": [product("1", "4.86")]}]}
            )

    entries = list(MercadonaClient(warehouse="svq1", delay=0, session=Session()).iter_catalog())

    assert [(e.product["id"], e.subcategory["name"]) for e in entries] == [("1", "Leche desnatada")]
