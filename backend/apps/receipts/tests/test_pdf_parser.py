import io
from decimal import Decimal

import pytest

from apps.receipts.parsing import ReceiptParseError, parse_pdf


def test_parse_generated_pdf(sample_pdf):
    receipt = parse_pdf(io.BytesIO(sample_pdf))

    assert receipt.invoice_number == "1234-001-000001"
    assert len(receipt.lines) == 14
    assert receipt.total == Decimal("43.55")
    assert receipt.totals_match


def test_not_a_pdf():
    with pytest.raises(ReceiptParseError, match="Cannot read PDF"):
        parse_pdf(io.BytesIO(b"not a pdf"))
