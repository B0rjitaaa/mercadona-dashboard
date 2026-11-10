"""Parse the plain text of a Mercadona receipt into a ParsedReceipt.

Expected layout (one item per line once extracted from the PDF):

    MERCADONA, S.A. A-46103834
    CALLE EJEMPLO, 1
    28001 MADRID
    TELÉFONO: 910000000
    15/01/2026 10:30 OP: 1000001
    FACTURA SIMPLIFICADA: 1234-001-000001
    Cnt. Descripción P. Unit Importe
    1 LECHE DESN P6 4,86
    2 SALMOREJO FRESCO 1,65 3,30
    1 PLATANO
    0,728 kg 3,20 €/kg 2,33
    TOTAL (€) 43,55
    TARJETA BANCARIA 43,55
    IVA BASE IMP. (€) CUOTA (€) TOTAL (€)
    4% 9,13 0,36 9,49
    TOTAL 39,47 4,08 43,55
    TARJ. BANCARIA: **** **** **** 1234
"""

import re
from datetime import datetime
from decimal import Decimal

from .errors import ReceiptParseError
from .types import LineType, ParsedLine, ParsedReceipt, ReceiptKind, Unit, VatRate

AMOUNT = r"-?\d+(?:\.\d{3})*,\d{2}"

RE_COMPANY = re.compile(r"^(?P<name>.+?)\s+(?P<tax_id>[A-Z]-?\d{7,8}[A-Z0-9]?)$")
RE_POSTAL = re.compile(r"^(?P<postal>\d{5})\s+(?P<city>.+)$")
RE_PHONE = re.compile(r"^TEL[ÉE]FONO:?\s*(?P<phone>[\d ]+)$", re.IGNORECASE)
RE_DATE_OP = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})(?:\s+OP:?\s*(?P<op>\d+))?"
)
RE_INVOICE = re.compile(r"FACTURA\s+SIMPLIFICADA:?\s*(?P<number>[\d-]+)", re.IGNORECASE)
RE_RETURN_NUMBER = re.compile(r"^DEVOLUCI[ÓO]N:?\s*(?P<number>\d[\d-]+)$", re.IGNORECASE)
RE_ORIGINAL_INVOICE = re.compile(
    r"FRA\.?\s+SIMPLIF\.?\s+ORIGEN:?\s*(?P<number>[\d-]+)", re.IGNORECASE
)
RE_BANNER = re.compile(r"^\*+.*\*+$")  # e.g. "***** DEVOLUCIÓN *****"
# Newer receipts: "Cnt. Descripción P. Unit Importe"; older ones lack "Cnt."
RE_ITEMS_HEADER = re.compile(r"^(?:Cnt\.?\s+)?Descripci[óo]n\s+P\.?\s*Unit", re.IGNORECASE)
RE_TOTAL = re.compile(rf"^TOTAL\s*\(€\)\s*(?P<amount>{AMOUNT})$", re.IGNORECASE)

RE_ITEM_UNIT_PRICE = re.compile(
    rf"^(?P<qty>-?\d+)\s+(?P<desc>.+?)\s+(?P<unit_price>{AMOUNT})\s+(?P<amount>{AMOUNT})$"
)
RE_ITEM = re.compile(rf"^(?P<qty>-?\d+)\s+(?P<desc>.+?)\s+(?P<amount>{AMOUNT})$")
RE_ITEM_NO_AMOUNT = re.compile(r"^(?P<qty>-?\d+)\s+(?P<desc>\D.*)$")
RE_WEIGHT = re.compile(
    rf"^(?P<kg>\d+,\d{{1,3}})\s*kg\s+(?P<price>{AMOUNT})\s*€/kg\s+(?P<amount>{AMOUNT})$",
    re.IGNORECASE,
)
RE_PAYMENT = re.compile(rf"^(?P<method>\D.+?)\s+(?P<amount>{AMOUNT})$")
RE_VAT_HEADER = re.compile(r"^IVA\s+BASE\s+IMP", re.IGNORECASE)
RE_VAT_ROW = re.compile(
    rf"^(?P<rate>\d+(?:,\d+)?)\s*%\s+(?P<base>{AMOUNT})\s+(?P<tax>{AMOUNT})"
    rf"(?:\s+(?P<total>{AMOUNT}))?$"
)

OTHER_KEYWORDS = ("PARKING", "APARCAMIENTO")


def to_decimal(value: str) -> Decimal:
    """Convert a Spanish formatted number ('1.234,56') to Decimal."""
    return Decimal(value.replace(".", "").replace(",", "."))


def normalise_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def parse_text(text: str) -> ParsedReceipt:
    lines = normalise_lines(text)
    receipt = ParsedReceipt()

    try:
        items_start = next(i for i, line in enumerate(lines) if RE_ITEMS_HEADER.match(line))
    except StopIteration as exc:
        raise ReceiptParseError("Items header ('Descripción P. Unit Importe') not found") from exc

    _parse_header(lines[:items_start], receipt)
    rest = _parse_items(lines[items_start + 1 :], receipt)
    _parse_footer(rest, receipt)

    if not receipt.invoice_number:
        raise ReceiptParseError("Simplified invoice number not found")
    if receipt.total is None:
        raise ReceiptParseError("TOTAL line not found")
    if not receipt.lines:
        raise ReceiptParseError("No receipt lines found")

    return receipt


def _parse_header(lines: list[str], receipt: ParsedReceipt) -> None:
    for i, line in enumerate(lines):
        if not receipt.tax_id and (m := RE_COMPANY.match(line)):
            receipt.company_name = m["name"].rstrip(",").strip()
            receipt.tax_id = m["tax_id"]
            following = [x for x in lines[i + 1 : i + 3] if not RE_BANNER.match(x)]
            if following and not RE_POSTAL.match(following[0]):
                receipt.store_address = following[0]
        elif RE_BANNER.match(line):
            if "DEVOLUCI" in line.upper():
                receipt.kind = ReceiptKind.RETURN
        elif not receipt.postal_code and (m := RE_POSTAL.match(line)):
            receipt.postal_code = m["postal"]
            receipt.city = m["city"]
        elif m := RE_PHONE.match(line):
            receipt.phone = m["phone"].replace(" ", "")
        elif m := RE_INVOICE.search(line):
            receipt.invoice_number = m["number"]
        elif m := RE_RETURN_NUMBER.match(line):
            receipt.kind = ReceiptKind.RETURN
            receipt.invoice_number = m["number"]
        elif m := RE_ORIGINAL_INVOICE.search(line):
            receipt.original_invoice_number = m["number"]
        elif m := RE_DATE_OP.search(line):
            receipt.issued_at = datetime.strptime(f"{m['date']} {m['time']}", "%d/%m/%Y %H:%M")
            receipt.operation_number = m["op"] or ""


def _line_type(description: str, amount: Decimal, kind: ReceiptKind) -> LineType:
    if kind == ReceiptKind.RETURN:
        return LineType.RETURN
    if amount < 0:
        return LineType.DISCOUNT
    if any(keyword in description.upper() for keyword in OTHER_KEYWORDS):
        return LineType.OTHER
    return LineType.PRODUCT


def _parse_items(lines: list[str], receipt: ParsedReceipt) -> list[str]:
    """Parse item lines until TOTAL. Returns the remaining lines (footer)."""
    pending_weighed: tuple[int, str] | None = None  # (qty, description) awaiting weight line

    def add(description: str, quantity: Decimal, unit: Unit, unit_price: Decimal, amount: Decimal):
        receipt.lines.append(
            ParsedLine(
                position=len(receipt.lines) + 1,
                line_type=_line_type(description, amount, receipt.kind),
                description=description,
                quantity=quantity,
                unit=unit,
                unit_price=unit_price,
                amount=amount,
            )
        )

    for i, line in enumerate(lines):
        if m := RE_TOTAL.match(line):
            receipt.total = to_decimal(m["amount"])
            if pending_weighed:
                receipt.warnings.append(f"Item without amount: '{pending_weighed[1]}'")
            return lines[i + 1 :]

        if pending_weighed:
            _, description = pending_weighed
            pending_weighed = None
            if m := RE_WEIGHT.match(line):
                add(
                    description,
                    to_decimal(m["kg"]),
                    Unit.KG,
                    to_decimal(m["price"]),
                    to_decimal(m["amount"]),
                )
                continue
            receipt.warnings.append(f"Item without amount: '{description}'")

        if m := RE_ITEM_UNIT_PRICE.match(line):
            qty, unit_price, amount = (
                int(m["qty"]),
                to_decimal(m["unit_price"]),
                to_decimal(m["amount"]),
            )
            # Guard against descriptions that end in a number: only accept the
            # unit-price form when quantity x unit price equals the amount.
            if qty * unit_price == amount:
                add(m["desc"], Decimal(qty), Unit.UNIT, unit_price, amount)
                continue
            # Returned items ("-1 RESERVA LONCHAS 25,00 -4,50") print a middle value
            # that is not the unit price: derive the price from the amount instead.
            if qty < 0 and amount < 0:
                unit_price = (amount / qty).quantize(Decimal("0.01"))
                add(m["desc"], Decimal(qty), Unit.UNIT, unit_price, amount)
                continue

        if m := RE_ITEM.match(line):
            qty, amount = int(m["qty"]), to_decimal(m["amount"])
            unit_price = (amount / qty).quantize(Decimal("0.01")) if qty else amount
            add(m["desc"], Decimal(qty), Unit.UNIT, unit_price, amount)
        elif m := RE_ITEM_NO_AMOUNT.match(line):
            pending_weighed = (int(m["qty"]), m["desc"])
        else:
            receipt.warnings.append(f"Unrecognised line: '{line}'")

    return []


def _parse_footer(lines: list[str], receipt: ParsedReceipt) -> None:
    in_vat = False
    for line in lines:
        if RE_VAT_HEADER.match(line):
            in_vat = True
            continue
        if in_vat:
            if m := RE_VAT_ROW.match(line):
                receipt.vat_breakdown.append(
                    VatRate(
                        rate=to_decimal(m["rate"]) if "," in m["rate"] else Decimal(m["rate"]),
                        base=to_decimal(m["base"]),
                        tax=to_decimal(m["tax"]),
                        total=to_decimal(m["total"]) if m["total"] else None,
                    )
                )
            continue
        if not receipt.payment_method and (m := RE_PAYMENT.match(line)):
            receipt.payment_method = m["method"]
