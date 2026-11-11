"""Fill an empty database with fictitious receipts and products.

For trying the app without Gmail and for the screenshots in the docs. Nothing here is real:
the store, receipts, prices and catalogue are made up. Refuses to touch a database that
already has receipts of its own.
"""

# ruff: noqa: E501  (the catalogue table reads better one product per line)

import hashlib
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.models import JobRun
from apps.products.models import CatalogPrice, Category, MatchSuggestion, Product, ProductAlias
from apps.receipts.models import Receipt, ReceiptLine, Store

PREFIX = "DEMO-"
CENT = Decimal("0.01")

# Section > category > subcategory ids are far above Mercadona's real ones
SECTIONS = {
    "dairy": (9001, "Lácteos y huevos", "Leche y yogures", "Básicos"),
    "fruit": (9002, "Fruta y verdura", "Fruta y verdura fresca", "De temporada"),
    "bakery": (9003, "Panadería y bollería", "Pan", "Pan del día y de molde"),
    "pantry": (9004, "Despensa", "Aceite, arroz y pasta", "Básicos de despensa"),
    "drinks": (9005, "Bebidas", "Agua y zumos", "Agua y zumos"),
    "cleaning": (9006, "Limpieza y hogar", "Ropa y papel", "Detergente y papel"),
    "meat": (9007, "Carne y pescado", "Carne y pescado fresco", "Bandejas"),
}

# (section, receipt description, catalogue name, packaging, price a year ago, price now,
#  purchases per 10 receipts, sold by kg)
CATALOGUE = [
    ("dairy", "LECHE SEMIDESNATADA", "Leche semidesnatada", "Brick 1 L", "0.89", "0.95", 8, False),
    ("dairy", "YOGUR NATURAL X8", "Yogur natural", "Pack 8 x 125 g", "1.45", "1.55", 5, False),
    ("dairy", "HUEVOS L 12", "Huevos frescos L", "Docena", "2.35", "2.60", 4, False),
    (
        "dairy",
        "QUESO TIERNO LONCHAS",
        "Queso tierno en lonchas",
        "Paquete 250 g",
        "2.10",
        "2.25",
        3,
        False,
    ),
    ("fruit", "PLATANO", "Plátano de Canarias", "Granel", "1.99", "2.19", 6, True),
    ("fruit", "TOMATE RAMA", "Tomate en rama", "Granel", "2.40", "2.29", 5, True),
    ("fruit", "MANZANA GOLDEN", "Manzana golden", "Bolsa 1 kg", "1.89", "1.99", 3, False),
    ("fruit", "AGUACATE", "Aguacate", "Malla 2 ud", "2.50", "2.75", 2, False),
    (
        "bakery",
        "PAN MOLDE INTEGRAL",
        "Pan de molde integral",
        "Paquete 460 g",
        "1.30",
        "1.40",
        5,
        False,
    ),
    ("bakery", "BARRA PAN", "Barra de pan", "Pieza 250 g", "0.45", "0.50", 7, False),
    (
        "pantry",
        "ACEITE OLIVA VIRGEN EX",
        "Aceite de oliva virgen extra",
        "Botella 1 L",
        "8.95",
        "5.95",
        2,
        False,
    ),
    ("pantry", "ARROZ REDONDO", "Arroz redondo", "Paquete 1 kg", "1.25", "1.35", 2, False),
    ("pantry", "PASTA ESPAGUETI", "Espaguetis", "Paquete 500 g", "0.80", "0.85", 3, False),
    (
        "pantry",
        "CAFE MOLIDO NATURAL",
        "Café molido natural",
        "Paquete 250 g",
        "2.60",
        "3.20",
        2,
        False,
    ),
    ("pantry", "TOMATE TRITURADO", "Tomate triturado", "Lata 400 g", "0.65", "0.70", 3, False),
    ("drinks", "AGUA MINERAL 6X1,5L", "Agua mineral", "Pack 6 x 1,5 L", "1.74", "1.86", 4, False),
    ("drinks", "ZUMO NARANJA", "Zumo de naranja", "Brick 1 L", "1.20", "1.35", 2, False),
    (
        "cleaning",
        "DETERGENTE LIQUIDO",
        "Detergente líquido",
        "Botella 40 lavados",
        "5.50",
        "5.80",
        1,
        False,
    ),
    (
        "cleaning",
        "PAPEL HIGIENICO",
        "Papel higiénico doble capa",
        "Paquete 12 rollos",
        "3.90",
        "4.10",
        2,
        False,
    ),
    (
        "meat",
        "PECHUGA POLLO",
        "Pechuga de pollo fileteada",
        "Bandeja 500 g",
        "3.45",
        "3.65",
        4,
        False,
    ),
    ("meat", "SALMON FRESCO", "Lomo de salmón", "Bandeja 2 ud", "5.20", "5.60", 2, False),
    ("meat", "CARNE PICADA MIXTA", "Carne picada mixta", "Bandeja 400 g", "2.90", "3.10", 3, False),
]

RECENT_CHANGES = {"ACEITE OLIVA VIRGEN EX", "CAFE MOLIDO NATURAL"}

# Bought but not identified yet: they show up in Review
UNIDENTIFIED = [("GALLETA CHOCO", "1.65", "bakery"), ("HUMMUS CLASICO", "1.80", "pantry")]


class Command(BaseCommand):
    help = "Fill an empty database with fictitious receipts and products (demo/screenshots)."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=26)
        parser.add_argument("--flush", action="store_true", help="Delete the demo data first.")
        parser.add_argument("--remove", action="store_true", help="Only delete the demo data.")

    def handle(self, *args, months: int, flush: bool, remove: bool, **options):
        if Receipt.objects.exclude(invoice_number__startswith=PREFIX).exists():
            raise CommandError("This database has real receipts. Use an empty database.")
        if flush or remove:
            self._flush()
        if remove:
            self.stdout.write(self.style.SUCCESS("Demo data removed."))
            return
        if Receipt.objects.exists():
            raise CommandError("Demo data is already there. Use --flush to recreate it.")
        with transaction.atomic():
            receipts = self._seed(months)
        self.stdout.write(self.style.SUCCESS(f"Created {receipts} demo receipts."))

    def _flush(self):
        Receipt.objects.filter(invoice_number__startswith=PREFIX).delete()
        Store.objects.filter(code="9999").delete()
        MatchSuggestion.objects.all().delete()
        ProductAlias.objects.filter(product__mercadona_id__startswith=PREFIX).delete()
        Product.objects.filter(mercadona_id__startswith=PREFIX).delete()
        Category.objects.filter(id__gte=9000).delete()
        JobRun.objects.all().delete()

    def _seed(self, months: int) -> int:
        rng = random.Random(42)
        today = timezone.localdate()
        start = today - timedelta(days=months * 30)

        products = self._catalogue(start, today)
        store = Store.objects.create(
            code="9999", address="Calle Ejemplo 1", postal_code="00000", city="Demo"
        )

        count, day = 0, start
        while day <= today:
            # Two or three shops a week, a bigger one at the weekend
            if day.weekday() in (1, 3, 5) and rng.random() < 0.8:
                count += 1
                self._receipt(rng, store, day, count, products, big=day.weekday() == 5)
            day += timedelta(days=1)

        for run in (
            ("sync_catalog", {"products": len(products), "price_changes": 6}),
            ("match_products", {"checked": 2, "auto_linked": 0, "suggested": 2}),
            ("sync_gmail", {"messages": count, "receipts_created": count}),
        ):
            job, stats = run
            JobRun.objects.create(
                job=job, status=JobRun.Status.SUCCESS, stats=stats, finished_at=timezone.now()
            )
        return count

    def _catalogue(self, start, today) -> list[tuple]:
        result = []
        for section_id, name, category_name, subcategory_name in SECTIONS.values():
            section = Category.objects.create(id=section_id, name=name, level=0)
            category = Category.objects.create(
                id=section_id + 100, name=category_name, level=1, parent=section
            )
            Category.objects.create(
                id=section_id + 200, name=subcategory_name, level=2, parent=category
            )
        for i, (key, desc, name, packaging, old, new, weight, by_kg) in enumerate(CATALOGUE, 1):
            old, new = Decimal(old), Decimal(new)
            product = Product.objects.create(
                mercadona_id=f"{PREFIX}{i}",
                name=name,
                packaging=packaging,
                category_id=SECTIONS[key][0] + 200,
                unit_price=new,
                bulk_price=new if by_kg else None,
                reference_format="kg" if by_kg else "",
                last_seen_at=timezone.now(),
            )
            CatalogPrice.objects.create(product=product, date=start, unit_price=old)
            # Spread the price changes over the last months; a few happen this week
            changed = today - timedelta(days=(i * 11) % 150 + 2)
            if desc in RECENT_CHANGES:  # after the last purchase: shows up as a price alert
                changed = today - timedelta(days=1)
            changed = max(changed, start + timedelta(days=1))
            if new != old:
                CatalogPrice.objects.create(product=product, date=changed, unit_price=new)
            ProductAlias.objects.create(
                description=desc, product=product, source=ProductAlias.Source.AUTO, score="0.95"
            )
            result.append((product, desc, old, new, weight, by_kg, changed))
        for desc, _, key in UNIDENTIFIED:
            for rank, (product, *_rest) in enumerate(
                [r for r in result if r[0].category_id == SECTIONS[key][0] + 200][:3], 1
            ):
                MatchSuggestion.objects.create(
                    description=desc,
                    product=product,
                    score=Decimal("0.6") - Decimal(rank) / 10,
                    rank=rank,
                )
        return result

    def _receipt(self, rng, store, day, n, products, big):
        issued = timezone.make_aware(datetime.combine(day, time(rng.choice([10, 12, 18, 19]), 15)))
        receipt = Receipt.objects.create(
            pdf=f"demo/{n}.pdf",
            pdf_sha256=hashlib.sha256(f"demo-{n}".encode()).hexdigest(),
            source=Receipt.Source.GMAIL,
            status=Receipt.Status.PROCESSED,
            parsed_at=issued,
            invoice_number=f"{PREFIX}{n:05d}",
            store=store,
            issued_at=issued,
            payment_method="TARJETA BANCARIA",
            total=Decimal("0"),
        )
        total, position = Decimal("0"), 0
        boost = 1.8 if big else 0.9
        for product, desc, old, new, weight, by_kg, changed in products:
            if rng.random() > weight / 10 * boost:
                continue
            price = new if day >= changed else old
            quantity = (
                Decimal(str(round(rng.uniform(0.4, 1.6), 3)))
                if by_kg
                else Decimal(rng.choice([1, 1, 1, 2]))
            )
            position += 1
            amount = (quantity * price).quantize(CENT)
            ReceiptLine.objects.create(
                receipt=receipt,
                position=position,
                description=desc,
                quantity=quantity,
                unit=ReceiptLine.Unit.KG if by_kg else ReceiptLine.Unit.UNIT,
                unit_price=price,
                amount=amount,
                product=product,
            )
            total += amount
        for desc, price, _ in UNIDENTIFIED:
            if rng.random() < 0.25:
                position += 1
                ReceiptLine.objects.create(
                    receipt=receipt,
                    position=position,
                    description=desc,
                    quantity=Decimal(1),
                    unit_price=Decimal(price),
                    amount=Decimal(price),
                )
                total += Decimal(price)
        receipt.total = total
        receipt.save(update_fields=["total"])
