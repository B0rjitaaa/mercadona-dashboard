from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JobRun(models.Model):
    """Log of background job executions (NFR-05)."""

    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"

    job = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.job} {self.started_at:%Y-%m-%d %H:%M} ({self.status})"
