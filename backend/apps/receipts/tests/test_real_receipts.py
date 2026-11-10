"""Parser tests against real Mercadona receipts (local only).

- fixtures/private/*.pdf: the original PDFs.
- fixtures/real/*.txt: anonymised text versions of those PDFs.

Both folders are git-ignored (personal data), so these tests are skipped when empty.
"""

from pathlib import Path

import pytest

from apps.receipts.parsing import LineType, parse_pdf, parse_text

from .anonymise_fixtures import anonymise

FIXTURES = Path(__file__).parent / "fixtures"
TEXTS = sorted((FIXTURES / "real").glob("*.txt"))
PDFS = sorted((FIXTURES / "private").glob("*.pdf"))


@pytest.mark.parametrize("path", TEXTS, ids=lambda p: p.stem)
def test_real_receipt_text(path: Path):
    receipt = parse_text(path.read_text(encoding="utf-8"))

    assert receipt.warnings == []
    assert receipt.totals_match, f"lines={receipt.lines_total} total={receipt.total}"
    assert receipt.invoice_number
    assert receipt.issued_at is not None
    assert receipt.store_address and receipt.postal_code
    assert receipt.payment_method == "TARJETA BANCARIA"
    assert all(line.line_type == LineType.PRODUCT for line in receipt.lines)

    # File name is YYYY-MM-DD_<total>
    date, total = path.stem.split("_")
    assert receipt.issued_at.date().isoformat() == date
    assert str(receipt.total) == total

    # VAT table is consistent with the receipt total
    assert receipt.vat_breakdown
    assert sum(v.total for v in receipt.vat_breakdown) == receipt.total
    assert all(v.base + v.tax == v.total for v in receipt.vat_breakdown)


@pytest.mark.parametrize("path", PDFS, ids=lambda p: p.stem)
def test_real_receipt_pdf_matches_committed_text(path: Path):
    text_fixture = FIXTURES / "real" / f"{path.stem}.txt"
    assert text_fixture.exists(), "Run: python -m apps.receipts.tests.anonymise_fixtures"

    from_pdf = parse_pdf(path)
    from_text = parse_text(text_fixture.read_text(encoding="utf-8"))

    assert from_pdf.lines == from_text.lines
    assert from_pdf.total == from_text.total
    assert from_pdf.invoice_number == from_text.invoice_number


def test_anonymise():
    text = "TARJ. BANCARIA: **** **** **** 1234\nAUT: 654321 ARC: 00 AID: A0000000012345"

    assert anonymise(text) == (
        "TARJ. BANCARIA: **** **** **** 0000\nAUT: 000000 ARC: 00 AID: A0000000000000"
    )
