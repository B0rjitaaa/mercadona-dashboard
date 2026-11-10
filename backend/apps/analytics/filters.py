"""Query-string filters shared by the analytics endpoints (FR-14).

- Period: ``from`` / ``to`` as YYYY-MM-DD, both inclusive and optional.
- Sections: ``sections=12,15,none`` — top-level catalogue sections by id; ``none`` selects
  lines without a catalogue category (unidentified or manual products).
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db.models import Q
from rest_framework.exceptions import ValidationError

UNCATEGORISED = "none"


def shift_months(value: date, months: int) -> date:
    """Same day `months` later (or earlier), clipped to the length of the target month."""
    index = value.year * 12 + value.month - 1 + months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


@dataclass(frozen=True)
class Period:
    start: date | None = None
    end: date | None = None

    def q(self, prefix: str = "") -> Q:
        """Filter on a receipt's local issue date; `prefix` reaches it from lines ("receipt__")."""
        q = Q()
        if self.start:
            q &= Q(**{f"{prefix}issued_at__date__gte": self.start})
        if self.end:
            q &= Q(**{f"{prefix}issued_at__date__lte": self.end})
        return q

    def previous(self, today: date) -> "Period | None":
        """The comparable period right before this one.

        Periods starting on the 1st shift by whole months, so "1-10 Nov" compares with
        "1-10 Oct" and the last 12 months with the 12 months before; others shift by days.
        """
        if self.start is None:
            return None
        end = self.end or today
        if self.start.day == 1:
            months = (end.year - self.start.year) * 12 + end.month - self.start.month + 1
            return Period(shift_months(self.start, -months), shift_months(end, -months))
        length = (end - self.start).days + 1
        return Period(self.start - timedelta(days=length), self.start - timedelta(days=1))

    def as_dict(self) -> dict:
        return {
            "from": self.start.isoformat() if self.start else None,
            "to": self.end.isoformat() if self.end else None,
        }


@dataclass(frozen=True)
class Sections:
    ids: tuple[int, ...] = ()
    uncategorised: bool = False

    @property
    def active(self) -> bool:
        return bool(self.ids) or self.uncategorised

    def q(self) -> Q:
        """Filter on receipt lines. Products always hang from a level-3 category."""
        if not self.active:
            return Q()
        q = Q(product__category__parent__parent_id__in=self.ids) if self.ids else Q(pk__in=[])
        if self.uncategorised:
            q |= Q(product__isnull=True) | Q(product__category__isnull=True)
        return q

    def as_list(self) -> list:
        return [*self.ids, *([UNCATEGORISED] if self.uncategorised else [])]


# Immutable "no filter" defaults
ALL_TIME = Period()
ALL_SECTIONS = Sections()


def _parse_date(value: str | None, name: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError({name: "Expected YYYY-MM-DD."}) from exc


def parse_period(params, prefix: str = "") -> Period:
    start = _parse_date(params.get(f"{prefix}from"), f"{prefix}from")
    end = _parse_date(params.get(f"{prefix}to"), f"{prefix}to")
    if start and end and start > end:
        raise ValidationError({f"{prefix}from": "Must be on or before 'to'."})
    return Period(start, end)


def parse_sections(params) -> Sections:
    ids, uncategorised = [], False
    for token in filter(None, (t.strip() for t in params.get("sections", "").split(","))):
        if token == UNCATEGORISED:
            uncategorised = True
        elif token.isdigit():
            ids.append(int(token))
        else:
            raise ValidationError({"sections": "Expected section ids or 'none', comma separated."})
    return Sections(tuple(sorted(set(ids))), uncategorised)
