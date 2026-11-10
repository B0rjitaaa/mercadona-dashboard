"""Match abbreviated receipt descriptions to catalogue products (FR-04).

Pure Python (no Django) so it can be tested and tuned in isolation.

Score = 0.7 x text score + 0.3 x price score
- text: weighted share of receipt tokens that are a prefix of a word in the product name
  or packaging ("DESN" -> "desnatada"); the first token (usually the product type) weighs
  more, numbers weigh less.
- price: how close the paid price is to the current catalogue price (per kg for weighed
  products). 0% off -> 1, 25% or more off -> 0.
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

TEXT_WEIGHT = Decimal("0.7")
PRICE_WEIGHT = Decimal("0.3")
MIN_TEXT_SCORE = 0.4
AUTO_LINK_SCORE = Decimal("0.85")
AUTO_LINK_MARGIN = Decimal("0.08")

# Abbreviations seen on Mercadona receipts that are not plain prefixes.
ABBREVIATIONS: dict[str, list[str]] = {
    "LS": ["LISTO"],  # "LS LENTEJAS" -> "Lentejas Listo para Comer"
    "Q": ["QUESO"],
    "HAMB": ["HAMBURGUESA"],
    "BEB": ["BEBIDA"],
}


def normalise(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.upper())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("1/2", " MEDIA ")
    text = re.sub(r"\bP-?(\d+)\b", r" PACK \1 ", text)  # P6 / P-3 -> PACK 6
    text = re.sub(r"(\d)([A-Z])", r"\1 \2", text)  # 500G -> 500 G
    tokens: list[str] = []
    for token in re.sub(r"[^A-Z0-9%]+", " ", text).split():
        tokens.extend(ABBREVIATIONS.get(token, [token]))
    return tokens


@dataclass
class CatalogItem:
    id: int
    name: str
    packaging: str = ""
    unit_price: Decimal | None = None
    bulk_price: Decimal | None = None
    words: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.words:
            self.words = normalise(f"{self.name} {self.packaging}")


@dataclass(frozen=True)
class Candidate:
    item_id: int
    score: Decimal
    text_score: Decimal


def _token_matches(token: str, word: str) -> bool:
    """Receipt token is an abbreviation of the word ("DESN" -> "DESNATADA"), or the word is
    the token minus a short ending (plural: "PIMIENTOS" -> "PIMIENTO"). A long token must
    not match a short word it merely starts with ("PARAGUAYO" is not "PARA")."""
    if word.startswith(token):
        return True
    return len(word) >= 4 and token.startswith(word) and len(token) - len(word) <= 2


def text_score(tokens: list[str], words: list[str]) -> float:
    total = matched = 0.0
    for i, token in enumerate(tokens):
        weight = 2.0 if token.isdigit() else float(len(token))
        if i == 0:
            weight *= 1.5
        total += weight
        if any(_token_matches(token, w) for w in words):
            matched += weight
    return matched / total if total else 0.0


def price_score(paid: Decimal | None, unit: str, item: CatalogItem) -> Decimal:
    reference = item.bulk_price if unit == "kg" else item.unit_price
    if not paid or not reference:
        return Decimal("0")
    diff = abs(paid - reference) / reference
    return max(Decimal("0"), Decimal("1") - diff * 4)


def is_confident(candidates: list[Candidate]) -> bool:
    if not candidates or candidates[0].score < AUTO_LINK_SCORE:
        return False
    return len(candidates) == 1 or candidates[0].score - candidates[1].score >= AUTO_LINK_MARGIN


class Matcher:
    def __init__(self, items: list[CatalogItem]):
        self.items = {item.id: item for item in items}
        # Inverted index on the first two letters of every word, to avoid scoring
        # every product for every description.
        self.index: dict[str, set[int]] = defaultdict(set)
        for item in items:
            for word in item.words:
                self.index[word[:2]].add(item.id)

    def _pool(self, tokens: list[str]) -> set[int]:
        pool: set[int] = set()
        for token in tokens:
            if len(token) >= 2 and not token.isdigit():
                pool |= self.index.get(token[:2], set())
        return pool

    def candidates(
        self, description: str, paid: Decimal | None = None, unit: str = "unit", limit: int = 3
    ) -> list[Candidate]:
        tokens = normalise(description)
        scored = []
        for item_id in self._pool(tokens):
            item = self.items[item_id]
            ts = text_score(tokens, item.words)
            if ts < MIN_TEXT_SCORE:
                continue
            text = Decimal(str(round(ts, 3)))
            score = TEXT_WEIGHT * text + PRICE_WEIGHT * price_score(paid, unit, item)
            scored.append(Candidate(item_id, score.quantize(Decimal("0.001")), text))
        scored.sort(key=lambda c: (-c.score, -c.text_score, self.items[c.item_id].name))
        return scored[:limit]

    def search(self, query: str, limit: int = 20) -> list[int]:
        """Free-text catalogue search for the review screen (no price involved)."""
        return [c.item_id for c in self.candidates(query, limit=limit)]
