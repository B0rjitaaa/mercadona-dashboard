from pathlib import Path
from typing import BinaryIO

import pdfplumber

from .errors import ReceiptParseError
from .text_parser import parse_text
from .types import ParsedReceipt


def extract_text(source: str | Path | BinaryIO) -> str:
    try:
        with pdfplumber.open(source) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:  # pdfplumber raises several unrelated exception types
        raise ReceiptParseError(f"Cannot read PDF: {exc}") from exc


def parse_pdf(source: str | Path | BinaryIO) -> ParsedReceipt:
    return parse_text(extract_text(source))
