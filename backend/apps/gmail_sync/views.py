from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.models import JobRun
from apps.core.serializers import JobRunSerializer

from .services import JOB_NAME
from .tasks import sync_gmail_task


@api_view(["GET"])
def gmail_status(request):
    last_run = JobRun.objects.filter(job=JOB_NAME).first()
    return Response(
        {
            "credentials_configured": Path(settings.GMAIL_CREDENTIALS_FILE).exists(),
            "authorised": Path(settings.GMAIL_TOKEN_FILE).exists(),
            "query": settings.GMAIL_QUERY,
            "last_run": JobRunSerializer(last_run).data if last_run else None,
        }
    )


@api_view(["POST"])
def gmail_sync(request):
    """ "Sync now" (FR-01)."""
    result = sync_gmail_task.delay()
    return Response({"task_id": result.id}, status=status.HTTP_202_ACCEPTED)
