from django.db import models

from apps.core.models import TimeStampedModel


class Category(models.Model):
    """Mercadona category tree: section (0) > category (1) > subcategory (2)."""

    id = models.PositiveIntegerField(primary_key=True)  # Mercadona's id
    name = models.CharField(max_length=200)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="children")
    level = models.PositiveSmallIntegerField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["level", "order", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    @property
    def section(self) -> "Category":
        node = self
        while node.parent_id:
            node = node.parent
        return node


class Product(TimeStampedModel):
    mercadona_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    name = models.CharField(max_length=300)
    packaging = models.CharField(max_length=100, blank=True)
    thumbnail = models.URLField(max_length=500, blank=True)
    share_url = models.URLField(max_length=500, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )

    # Current catalogue price
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bulk_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    reference_format = models.CharField(max_length=10, blank=True)  # "L", "kg"...
    size_format = models.CharField(max_length=10, blank=True)
    unit_size = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    is_manual = models.BooleanField(default=False)  # created by the user, not in the catalogue
    is_active = models.BooleanField(default=True)  # False once it leaves the catalogue
    last_seen_at = models.DateTimeField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.packaging})" if self.packaging else self.name


class CatalogPrice(models.Model):
    """Catalogue price history: one row per product each time its price changes (FR-05)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="catalog_prices")
    date = models.DateField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    bulk_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        ordering = ["product", "date"]
        constraints = [
            models.UniqueConstraint(fields=["product", "date"], name="unique_catalog_price_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.product_id} {self.date}: {self.unit_price}"


class ProductAlias(TimeStampedModel):
    """A receipt description linked to a product (FR-04)."""

    class Source(models.TextChoices):
        AUTO = "auto"
        MANUAL = "manual"

    description = models.CharField(max_length=200, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="aliases")
    source = models.CharField(max_length=10, choices=Source.choices)
    score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    class Meta:
        ordering = ["description"]
        verbose_name_plural = "product aliases"

    def __str__(self) -> str:
        return f"{self.description} → {self.product}"


class MatchSuggestion(models.Model):
    """Candidate products for a receipt description that has no alias yet."""

    description = models.CharField(max_length=200, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    score = models.DecimalField(max_digits=4, decimal_places=3)
    rank = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["description", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["description", "product"], name="unique_suggestion")
        ]

    def __str__(self) -> str:
        return f"{self.description} #{self.rank} → {self.product_id} ({self.score})"
