"""Weekly email report (FR-15).

Covers the 7 days before the day it runs (Monday → the previous Monday to Sunday) and is
sent from the receipts Gmail account to REPORT_EMAIL_TO.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.utils import timezone

from apps.analytics import prices
from apps.analytics.filters import Period
from apps.analytics.services import ZERO, counted_receipts, overview, totals
from apps.core.models import JobRun
from apps.gmail_sync.client import SEND_SCOPE, GmailClient, granted_scopes
from apps.products.services import unmatched_descriptions
from apps.receipts.models import Receipt

logger = logging.getLogger(__name__)

JOB_NAME = "weekly_report"

STRINGS = {
    "es": {
        "subject": "Mercadona · semana del {start} al {end}: {total}",
        "title": "Tu semana en Mercadona",
        "week": "Gasto de la semana",
        "receipts_one": "{count} ticket",
        "receipts_other": "{count} tickets",
        "no_receipts": "Esta semana no hay tickets.",
        "vs_average": "{pct} frente a tu media de las 4 semanas anteriores ({average})",
        "month": "En lo que va de {month}",
        "tickets": "Tickets",
        "top": "Lo que más te ha costado",
        "price_changes": "Cambios de precio esta semana",
        "price_changes_hint": "Productos que compras a menudo y han cambiado de precio en Mercadona.",  # noqa: E501
        "alerts": "Más caros que la última vez que los compraste",
        "impact": "Impacto en un año: {value}",
        "to_do": "Pendiente",
        "unmatched_one": "{count} producto nuevo sin identificar",
        "unmatched_other": "{count} productos nuevos sin identificar",
        "check_links_one": "{count} enlace de producto que conviene revisar",
        "check_links_other": "{count} enlaces de producto que conviene revisar",
        "pending_receipts_one": "{count} ticket por revisar o con error",
        "pending_receipts_other": "{count} tickets por revisar o con error",
        "failed_jobs": "Tareas que han fallado: {jobs}",
        "open": "Abrir Mercadona Dashboard",
        "footer": "Resumen automático de Mercadona Dashboard. Cambia el destinatario o el día en el .env del servidor.",  # noqa: E501
        "return": "devolución",
        "months": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",  # noqa: E501
        "months_short": "ene feb mar abr may jun jul ago sept oct nov dic",
        "jobs": {
            "sync_gmail": "importar tickets de Gmail",
            "sync_catalog": "descargar el catálogo",
            "match_products": "identificar productos",
        },
    },
    "en": {
        "subject": "Mercadona · week of {start} – {end}: {total}",
        "title": "Your week at Mercadona",
        "week": "Spent this week",
        "receipts_one": "{count} receipt",
        "receipts_other": "{count} receipts",
        "no_receipts": "No receipts this week.",
        "vs_average": "{pct} vs your average of the previous 4 weeks ({average})",
        "month": "So far in {month}",
        "tickets": "Receipts",
        "top": "What cost you the most",
        "price_changes": "Price changes this week",
        "price_changes_hint": "Products you buy often whose price changed at Mercadona.",
        "alerts": "Dearer than the last time you bought them",
        "impact": "Yearly impact: {value}",
        "to_do": "To do",
        "unmatched_one": "{count} new unidentified product",
        "unmatched_other": "{count} new unidentified products",
        "check_links_one": "{count} product link worth checking",
        "check_links_other": "{count} product links worth checking",
        "pending_receipts_one": "{count} receipt to review or with errors",
        "pending_receipts_other": "{count} receipts to review or with errors",
        "failed_jobs": "Failed jobs: {jobs}",
        "open": "Open Mercadona Dashboard",
        "footer": "Automatic summary from Mercadona Dashboard. Change the recipient or the day in the server's .env.",  # noqa: E501
        "return": "return",
        "months": "January February March April May June July August September October November December",  # noqa: E501
        "months_short": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec",
        "jobs": {
            "sync_gmail": "import receipts from Gmail",
            "sync_catalog": "download the catalogue",
            "match_products": "identify products",
        },
    },
}


class Formatter:
    def __init__(self, language: str):
        self.lang = language if language in STRINGS else "es"
        self.s = STRINGS[self.lang]

    def t(self, key: str, count: int | None = None, **kwargs) -> str:
        if count is not None:
            key = f"{key}_{'one' if count == 1 else 'other'}"
            kwargs["count"] = count
        return self.s[key].format(**kwargs)

    def money(self, value: Decimal | None) -> str:
        value = value or ZERO
        text = f"{abs(value):,.2f}"
        sign = "-" if value < 0 else ""
        if self.lang == "es":
            return f"{sign}{text.replace(',', ' ').replace('.', ',').replace(' ', '.')} €"
        return f"{sign}€{text}"

    def pct(self, value: Decimal | float) -> str:
        value = Decimal(str(value)).quantize(Decimal("0.1"))
        text = f"{value:+}".replace(".", ",") if self.lang == "es" else f"{value:+}"
        return f"{text} %" if self.lang == "es" else f"{text}%"

    def day(self, value: date) -> str:
        month = self.s["months_short"].split()[value.month - 1]
        return f"{value.day} {month}" if self.lang == "es" else f"{month} {value.day}"

    def month(self, value: date) -> str:
        return self.s["months"].split()[value.month - 1]


def week_bounds(today: date) -> Period:
    return Period(today - timedelta(days=7), today - timedelta(days=1))


def build(today: date | None = None) -> dict:
    """Raw report data for the 7 days before `today`."""
    today = today or timezone.localdate()
    week = week_bounds(today)
    before = Period(week.start - timedelta(days=28), week.start - timedelta(days=1))
    watch = prices.price_watch(7)
    pending = Receipt.objects.aggregate(
        count=Count("id", filter=Q(status__in=[Receipt.Status.NEEDS_REVIEW, Receipt.Status.ERROR]))
    )["count"]
    failed = (
        JobRun.objects.filter(started_at__date__gte=week.start, status=JobRun.Status.FAILED)
        .exclude(job=JOB_NAME)
        .values_list("job", flat=True)
        .distinct()
    )
    return {
        "period": week,
        "week": totals(week),
        "average_week": (totals(before)["total"] / 4).quantize(Decimal("0.01")),
        "month": totals(Period(week.end.replace(day=1), week.end)),
        "receipts": list(
            counted_receipts()
            .filter(week.q())
            .order_by("issued_at")
            .values("id", "issued_at", "total", "kind")
        ),
        "top": overview(week)["by_spend"][:5],
        "price_changes": watch["recent_changes"][:8],
        "alerts": [a for a in watch["alerts"] if a["diff"] > 0][:5],
        "check_links": len(watch["check_links"]),
        "unmatched": len(unmatched_descriptions()),
        "pending_receipts": pending,
        "failed_jobs": sorted(set(failed)),
    }


def render(data: dict, language: str | None = None, base_url: str | None = None):
    """(subject, text, html) for the report data."""
    f = Formatter(language or settings.REPORT_LANGUAGE)
    base = (base_url or settings.REPORT_BASE_URL).rstrip("/")
    period, week = data["period"], data["week"]
    total, average = week["total"], data["average_week"]

    def item(row, **extra):
        path = (
            f"/products/{row['product_id']}"
            if row.get("product_id")
            else f"/products/unidentified/{quote(row['description'], safe='')}"
        )
        return {"name": row["name"], "url": base + path, **extra}

    to_do = []
    if data["unmatched"]:
        to_do.append((f.t("unmatched", data["unmatched"]), f"{base}/review"))
    if data["check_links"]:
        to_do.append((f.t("check_links", data["check_links"]), f"{base}/prices"))
    if data["pending_receipts"]:
        to_do.append((f.t("pending_receipts", data["pending_receipts"]), f"{base}/receipts"))
    if data["failed_jobs"]:
        jobs = ", ".join(f.s["jobs"].get(j, j) for j in data["failed_jobs"])
        to_do.append((f.t("failed_jobs", jobs=jobs), f"{base}/settings"))

    context = {
        "s": f.s,
        "base_url": base,
        "period": f"{f.day(period.start)} – {f.day(period.end)}",
        "total": f.money(total),
        "receipts_count": f.t("receipts", week["receipts"]),
        "vs_average": (
            f.t(
                "vs_average", pct=f.pct((total - average) / average * 100), average=f.money(average)
            )
            if average
            else ""
        ),
        "up": average and total > average,
        "month": f"{f.t('month', month=f.month(period.end))}: {f.money(data['month']['total'])}",
        "receipts": [
            {
                "date": f.day(timezone.localtime(r["issued_at"]).date()),
                "total": f.money(r["total"]),
                "url": f"{base}/receipts/{r['id']}",
                "is_return": r["kind"] == Receipt.Kind.RETURN,
            }
            for r in data["receipts"]
        ],
        "top": [item(r, value=f.money(r["spent"])) for r in data["top"]],
        "price_changes": [
            item(
                r,
                value=f"{f.money(r['catalog_previous'])} → {f.money(r['catalog_price'])}",
                pct=f.pct(r["catalog_change_pct"]),
                up=r["catalog_change_pct"] > 0,
            )
            for r in data["price_changes"]
        ],
        "alerts": [
            item(
                r,
                value=f"{f.money(r['last_paid'])} → {f.money(r['catalog_price'])}",
                pct=f.pct(r["diff_pct"]),
                impact=f.t("impact", value=f.money(r["impact_12m"])),
            )
            for r in data["alerts"]
        ],
        "to_do": to_do,
    }
    subject = f.t("subject", start=f.day(period.start), end=f.day(period.end), total=f.money(total))
    text = render_to_string("reports/weekly.txt", context).strip() + "\n"
    html = render_to_string("reports/weekly.html", context)
    return subject, text, html


def mask(address: str) -> str:
    """'someone@example.com' -> 'so…@example.com', to show who receives it without leaking it."""
    local, _, domain = address.partition("@")
    return f"{local[:2]}…@{domain}" if domain else "…"


def can_send() -> bool:
    return SEND_SCOPE in granted_scopes(settings.GMAIL_TOKEN_FILE)


def send_weekly(today: date | None = None, to: str | None = None) -> JobRun:
    run = JobRun.objects.create(job=JOB_NAME)
    recipient = to or settings.REPORT_EMAIL_TO
    try:
        if not recipient:
            run.stats = {"sent": 0, "skipped": 1}  # no recipient (REPORT_EMAIL_TO)
        elif not can_send():
            raise PermissionError(
                "The Gmail token cannot send email: run `make gmail-auth` again to add it."
            )
        else:
            subject, text, html = render(build(today))
            client = GmailClient.from_token_file(settings.GMAIL_TOKEN_FILE)
            client.send_email(recipient, subject, text, html)
            run.stats = {"sent": 1}
        run.status = JobRun.Status.SUCCESS
    except Exception as exc:
        logger.exception("Weekly report failed")
        run.status = JobRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
    run.finished_at = timezone.now()
    run.save()
    return run
