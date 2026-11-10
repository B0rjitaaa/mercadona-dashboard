from django.contrib import admin

from .models import GmailMessage


@admin.register(GmailMessage)
class GmailMessageAdmin(admin.ModelAdmin):
    list_display = ["received_at", "sender", "subject", "pdf_count", "status"]
    list_filter = ["status"]
    search_fields = ["subject", "sender", "message_id"]
