from django.contrib import admin

from .models import JobRun


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ["job", "status", "started_at", "finished_at", "stats"]
    list_filter = ["job", "status"]
    readonly_fields = ["job", "status", "started_at", "finished_at", "stats", "error"]
