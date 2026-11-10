from decimal import Decimal

import pytest

from apps.products.matching import CatalogItem, Matcher, is_confident, normalise, text_score

D = Decimal

CATALOG = [
    CatalogItem(1, "Leche desnatada Hacendado", "Pack-6", D("4.86")),
    CatalogItem(2, "Leche en polvo desnatada Hacendado", "Paquete", D("5.40")),
    CatalogItem(3, "Plátano de Canarias IGP", "Pieza", D("0.48"), D("3.20")),
    CatalogItem(4, "Lentejas Listo para Comer", "Bol", D("4.00")),
    CatalogItem(5, "Media tortilla de patata con calabacín Listo para Comer", "", D("4.75")),
    CatalogItem(6, "Preparado de verdura para puchero", "Bandeja", D("2.50")),
    CatalogItem(7, "Refresco Coca-Cola zero azúcar", "", D("4.18")),
    CatalogItem(8, "Refresco Coca-Cola zero azúcar zero cafeína", "", D("4.18")),
    CatalogItem(9, "Pimientos semipicantes", "Paquete", D("1.50")),
]


@pytest.fixture(scope="module")
def matcher():
    return Matcher(CATALOG)


@pytest.mark.parametrize(
    "text, tokens",
    [
        ("LECHE DESN P6", ["LECHE", "DESN", "PACK", "6"]),
        ("BURGER M VA/CE 500G", ["BURGER", "M", "VA", "CE", "500", "G"]),
        ("TORTILLA 1/2 PAT/CAL", ["TORTILLA", "MEDIA", "PAT", "CAL"]),
        ("LS LENTEJAS", ["LISTO", "LENTEJAS"]),
        ("Plátano", ["PLATANO"]),
    ],
)
def test_normalise(text, tokens):
    assert normalise(text) == tokens


def test_prefix_and_plural_rules():
    assert text_score(["DESN"], ["DESNATADA"]) == 1
    assert text_score(["PIMIENTO"], ["PIMIENTOS"]) == 1
    assert text_score(["PIMIENTOS"], ["PIMIENTO"]) == 1
    assert text_score(["PARAGUAYO"], ["PARA"]) == 0  # long token must not match a short word


@pytest.mark.parametrize(
    "description, paid, unit, expected",
    [
        ("LECHE DESN P6", "4.86", "unit", 1),
        ("PLATANO", "3.20", "kg", 3),
        ("LS LENTEJAS", "4.00", "unit", 4),
        ("TORTILLA 1/2 PAT/CAL", "4.75", "unit", 5),
        ("PIMIENTO SEMIPICANTE", "1.50", "unit", 9),
    ],
)
def test_best_candidate(matcher, description, paid, unit, expected):
    candidates = matcher.candidates(description, D(paid), unit)

    assert candidates[0].item_id == expected
    assert is_confident(candidates)


def test_price_breaks_ties_between_similar_names(matcher):
    candidates = matcher.candidates("LECHE DESN", D("5.40"))

    assert candidates[0].item_id == 2


def test_tie_is_not_confident(matcher):
    candidates = matcher.candidates("COLA ZERO ZERO", D("4.18"))

    assert {c.item_id for c in candidates[:2]} == {7, 8}
    assert not is_confident(candidates)


def test_no_candidates(matcher):
    assert matcher.candidates("PARAGUAYO BANDEJA", D("2.50")) == []
    assert not is_confident([])


def test_search(matcher):
    assert matcher.search("coca cola")[:2] in ([7, 8], [8, 7])
