"""Data structures returned by the parser. Pure Python, no Django."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class LineType(StrEnum):
    PRODUCT = "product"
    DISCOUNT = "discount"
    OTHER = "other"


class Unit(StrEnum):
    UNIT = "unit"
    KG = "kg"


@dataclass(frozen=True)
class ParsedLine:
    position: int
    line_type: LineType
    description: str
    quantity: Decimal
    unit: Unit
    unit_price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class VatRate:
    rate: Decimal  # percentage, e.g. Decimal("10")
    base: Decimal
    tax: Decimal


@dataclass
class ParsedReceipt:
    company_name: str = ""
    tax_id: str = ""
    store_address: str = ""
    postal_code: str = ""
    city: str = ""
    phone: str = ""
    issued_at: datetime | None = None  # naive, local time as printed on the receipt
    operation_number: str = ""
    invoice_number: str = ""
    total: Decimal | None = None
    payment_method: str = ""
    lines: list[ParsedLine] = field(default_factory=list)
    vat_breakdown: list[VatRate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def lines_total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0.00"))

    @property
    def totals_match(self) -> bool:
        return self.total is not None and self.lines_total == self.total
