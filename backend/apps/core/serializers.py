from rest_framework import serializers

from .models import JobRun


class JobRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRun
        fields = ["id", "job", "status", "started_at", "finished_at", "stats", "error"]
