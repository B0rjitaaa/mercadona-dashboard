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
        ("Cnt. Descripción P. Unit Importe\n1 PAN 1,00\nTOTAL (€) 1,00", "invoice number"),
        ("FACTURA SIMPLIFICADA: 1-1-1\nCnt. Descripción P. Unit Importe\n1 PAN 1,00", "TOTAL"),
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


OLD_FORMAT = """
MERCADONA, S.A. A-46103834
CTRA. EJEMPLO, 1
28001 Madrid
TELÉFONO: 910000000
20/03/2025 18:00 OP: 2000002
FACTURA SIMPLIFICADA: 1234-002-000002
Descripción P. Unit Importe
1 LIMON 1,85
2 ESPINACAS 1,24 2,48
1 PLATANO
1,242 kg 2,30 €/kg 2,86
TOTAL (€) 7,19
TARJETA BANCARIA 7,19
IVA BASE IMPONIBLE (€) CUOTA (€)
4% 6,91 0,28
TOTAL 6,91 0,28
TARJ. BANCARIA: **** **** **** 0000
N.C: 000000000 AUT: 000000
"""


def test_old_format_without_cnt_column():
    receipt = parse_text(OLD_FORMAT)

    assert receipt.totals_match
    assert receipt.warnings == []
    assert len(receipt.lines) == 3
    assert receipt.store_address == "CTRA. EJEMPLO, 1"
    assert receipt.city == "Madrid"
    assert receipt.store_code == "1234"
    assert receipt.vat_breakdown[0].total is None  # old VAT table has no total column


RETURN_RECEIPT = """
MERCADONA, S.A. A-46103834
***** DEVOLUCIÓN *****
CALLE EJEMPLO, 1
28001 MADRID
TELÉFONO: 910000000
14/09/2026 12:03 OP: 1000001
DEVOLUCIÓN: 1234-003-000003
FRA. SIMPLIF. ORIGEN: 1234-001-000001
Cnt. Descripción P. Unit Importe
-1 RESERVA LONCHAS 25,00 -4,50
TOTAL (€) -4,50
TARJETA BANCARIA -4,50
IVA BASE IMP. (€) CUOTA (€) TOTAL (€)
10% -4,09 -0,41 -4,50
TOTAL -4,09 -0,41 -4,50
"""


def test_return_receipt():
    from apps.receipts.parsing import ReceiptKind

    receipt = parse_text(RETURN_RECEIPT)

    assert receipt.kind == ReceiptKind.RETURN
    assert receipt.invoice_number == "1234-003-000003"
    assert receipt.original_invoice_number == "1234-001-000001"
    assert receipt.store_address == "CALLE EJEMPLO, 1"  # banner line skipped
    assert receipt.total == D("-4.50")
    assert receipt.totals_match
    [line] = receipt.lines
    assert line.line_type == LineType.RETURN
    assert line.description == "RESERVA LONCHAS"
    assert line.quantity == D("-1")
    assert line.unit_price == D("4.50")
    assert line.amount == D("-4.50")
    assert receipt.vat_breakdown[0].total == D("-4.50")


def test_sale_is_default_kind(sample_text):
    from apps.receipts.parsing import ReceiptKind

    receipt = parse_text(sample_text)

    assert receipt.kind == ReceiptKind.SALE
    assert receipt.original_invoice_number == ""
    assert receipt.store_code == "1234"
