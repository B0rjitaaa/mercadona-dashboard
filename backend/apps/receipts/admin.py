from django.contrib import admin

from .models import Receipt, ReceiptLine, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["address", "postal_code", "city", "chain"]
    search_fields = ["address", "city", "postal_code"]


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0
    fields = ["position", "line_type", "description", "quantity", "unit", "unit_price", "amount"]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "issued_at", "store", "total", "status", "source"]
    list_filter = ["status", "source", "store"]
    search_fields = ["invoice_number", "lines__description"]
    date_hierarchy = "issued_at"
    readonly_fields = ["pdf_sha256", "created_at", "updated_at", "parsed_at"]
    inlines = [ReceiptLineInline]
