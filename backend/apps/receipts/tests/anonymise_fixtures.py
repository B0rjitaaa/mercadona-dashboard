"""Create anonymised text fixtures from the real PDFs in fixtures/private/.

docker compose exec backend python -m apps.receipts.tests.anonymise_fixtures
"""

import re
from pathlib import Path

from apps.receipts.parsing import extract_text

FIXTURES = Path(__file__).parent / "fixtures"

REDACTIONS = [
    (re.compile(r"\*{4}( \*{4}){2} \d{4}"), "**** **** **** 0000"),
    (re.compile(r"AUT:\s*\d+"), "AUT: 000000"),
    (re.compile(r"AID:\s*\w+"), "AID: A0000000000000"),
    (re.compile(r"N\.C:\s*\d+"), "N.C: 000000000"),
]


def anonymise(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def main() -> None:
    for pdf in sorted((FIXTURES / "private").glob("*.pdf")):
        target = FIXTURES / "real" / f"{pdf.stem}.txt"
        target.write_text(anonymise(extract_text(pdf)) + "\n", encoding="utf-8")
        print(f"{pdf.name} -> {target.relative_to(FIXTURES)}")


if __name__ == "__main__":
    main()
