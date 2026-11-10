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
    assert receipt.store_code
    expected_type = LineType.RETURN if receipt.kind == "return" else LineType.PRODUCT
    assert all(line.line_type == expected_type for line in receipt.lines)

    # File name is YYYY-MM-DD_<total>
    date, total = path.stem.split("_")
    assert receipt.issued_at.date().isoformat() == date
    assert str(receipt.total) == total

    # VAT table is consistent with the receipt total
    assert receipt.vat_breakdown
    # Older receipts have no per-rate total column
    totals = [v.total if v.total is not None else v.base + v.tax for v in receipt.vat_breakdown]
    assert sum(totals) == receipt.total


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
    text = (
        "TARJ. BANCARIA: **** **** **** 1234\nN.C: 123456789 AUT: 654321\n"
        "ARC: 00 AID:\nA0000000012345"
    )

    assert anonymise(text) == (
        "TARJ. BANCARIA: **** **** **** 0000\nN.C: 000000000 AUT: 000000\n"
        "ARC: 00 AID: A0000000000000"
    )
