from django.contrib import admin

from .models import CatalogPrice, Category, MatchSuggestion, Product, ProductAlias


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "parent", "order"]
    list_filter = ["level"]
    search_fields = ["name"]


class AliasInline(admin.TabularInline):
    model = ProductAlias
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "packaging", "unit_price", "bulk_price", "is_active", "is_manual"]
    list_filter = ["is_active", "is_manual", "category__parent__parent"]
    search_fields = ["name", "mercadona_id", "aliases__description"]
    readonly_fields = ["raw", "last_seen_at", "created_at", "updated_at"]
    inlines = [AliasInline]


@admin.register(ProductAlias)
class ProductAliasAdmin(admin.ModelAdmin):
    list_display = ["description", "product", "source", "score"]
    list_filter = ["source"]
    search_fields = ["description", "product__name"]
    autocomplete_fields = ["product"]


@admin.register(CatalogPrice)
class CatalogPriceAdmin(admin.ModelAdmin):
    list_display = ["product", "date", "unit_price", "bulk_price"]
    search_fields = ["product__name"]


@admin.register(MatchSuggestion)
class MatchSuggestionAdmin(admin.ModelAdmin):
    list_display = ["description", "rank", "product", "score"]
    search_fields = ["description"]
