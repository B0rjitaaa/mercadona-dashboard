from datetime import datetime
from decimal import Decimal

import pytest

from apps.receipts.parsing import LineType, ReceiptParseError, Unit, parse_text
from apps.receipts.parsing.text_parser import to_decimal

D = Decimal


def test_header(sample_text):
    receipt = parse_text(sample_text)

    assert receipt.company_name == "MERCADONA, S.A."
    assert receipt.tax_id == "A-46103834"
    assert receipt.store_address == "CALLE EJEMPLO, 1"
    assert receipt.postal_code == "28001"
    assert receipt.city == "MADRID"
    assert receipt.phone == "910000000"
    assert receipt.issued_at == datetime(2026, 1, 15, 10, 30)
    assert receipt.operation_number == "1000001"
    assert receipt.invoice_number == "1234-001-000001"
    assert receipt.total == D("43.55")
    assert receipt.payment_method == "TARJETA BANCARIA"


def test_lines_and_totals(sample_text):
    receipt = parse_text(sample_text)

    assert len(receipt.lines) == 14
    assert [line.position for line in receipt.lines] == list(range(1, 15))
    assert receipt.lines_total == D("43.55")
    assert receipt.totals_match
    assert receipt.warnings == []


def test_single_unit_line(sample_text):
    line = parse_text(sample_text).lines[0]

    assert line.description == "LECHE DESN P6"
    assert line.quantity == D("1")
    assert line.unit == Unit.UNIT
    assert line.unit_price == D("4.86")
    assert line.amount == D("4.86")
    assert line.line_type == LineType.PRODUCT


def test_multiple_units_line(sample_text):
    line = parse_text(sample_text).lines[3]

    assert line.description == "SALMOREJO FRESCO"
    assert line.quantity == D("2")
    assert line.unit_price == D("1.65")
    assert line.amount == D("3.30")


def test_weighed_line(sample_text):
    line = parse_text(sample_text).lines[-1]

    assert line.description == "PLATANO"
    assert line.quantity == D("0.728")
    assert line.unit == Unit.KG
    assert line.unit_price == D("3.20")
    assert line.amount == D("2.33")


def test_description_with_special_characters(sample_text):
    descriptions = [line.description for line in parse_text(sample_text).lines]

    assert "BURGER M VA/CE 500G" in descriptions
    assert "TURRÓN COOKIES&CREAM" in descriptions
    assert "MAC BOLOÑESA" in descriptions


def test_vat_breakdown_and_discount():
    text = """
    MERCADONA, S.A. A-46103834
    CALLE EJEMPLO, 1
    28001 MADRID
    01/10/2026 10:00 OP: 1
    FACTURA SIMPLIFICADA: 1111-000-000001
    Cnt. Descripción P. Unit Importe
    1 PAN 1,00
    1 PARKING 0,50
    1 DESCUENTO -0,20
    TOTAL (€) 1,30
    EFECTIVO 5,00
    DEVOLUCIÓN 3,70
    IVA BASE IMPONIBLE (€) CUOTA (€)
    4% 0,96 0,04
    21% 0,25 0,05
    TOTAL 1,21 0,09
    """
    receipt = parse_text(text)

    assert [line.line_type for line in receipt.lines] == [
        LineType.PRODUCT,
        LineType.OTHER,
        LineType.DISCOUNT,
    ]
    assert receipt.totals_match
    assert receipt.payment_method == "EFECTIVO"
    assert [(v.rate, v.base, v.tax) for v in receipt.vat_breakdown] == [
        (D("4"), D("0.96"), D("0.04")),
        (D("21"), D("0.25"), D("0.05")),
    ]


def test_description_ending_in_price_like_number_is_not_split():
    text = """
    FACTURA SIMPLIFICADA: 1111-000-000002
    Cnt. Descripción P. Unit Importe
    1 PACK 6,00 OFERTA 3,00
    TOTAL (€) 3,00
    """
    line = parse_text(text).lines[0]

    # 1 x 6,00 != 3,00, so "6,00" belongs to the description
    assert line.description == "PACK 6,00 OFERTA"
    assert line.amount == D("3.00")


def test_totals_mismatch_is_reported(sample_text):
    receipt = parse_text(sample_text.replace("TOTAL (€) 43,55", "TOTAL (€) 50,00"))

    assert not receipt.totals_match


def test_unrecognised_lines_become_warnings(sample_text):
    text = sample_text.replace("1 COLA ZERO ZERO 4,18", "1 COLA ZERO ZERO 4,18\n*** PROMO ***")

    assert parse_text(text).warnings == ["Unrecognised line: '*** PROMO ***'"]


@pytest.mark.parametrize(
    "text, message",
    [
        ("hello world", "Items header"),
        ("Cnt. Descripción\n1 PAN 1,00\nTOTAL (€) 1,00", "invoice number"),
        ("FACTURA SIMPLIFICADA: 1-1-1\nCnt. Descripción\n1 PAN 1,00", "TOTAL"),
    ],
)
def test_invalid_documents(text, message):
    with pytest.raises(ReceiptParseError, match=message):
        parse_text(text)


@pytest.mark.parametrize(
    "value, expected", [("4,86", "4.86"), ("1.234,56", "1234.56"), ("-0,20", "-0.20")]
)
def test_to_decimal(value, expected):
    assert to_decimal(value) == D(expected)
