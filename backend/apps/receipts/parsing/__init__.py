"""Mercadona receipt PDF parser.

Pure Python: it must not import anything from Django. It takes a PDF and returns
dataclasses, so it can be tested in isolation against real PDFs in tests/fixtures/.
"""

from .errors import ReceiptParseError
from .pdf import extract_text, parse_pdf
from .text_parser import parse_text
from .types import LineType, ParsedLine, ParsedReceipt, ReceiptKind, Unit, VatRate

__all__ = [
    "LineType",
    "ParsedLine",
    "ParsedReceipt",
    "ReceiptKind",
    "ReceiptParseError",
    "Unit",
    "VatRate",
    "extract_text",
    "parse_pdf",
    "parse_text",
]
