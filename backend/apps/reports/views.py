from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.models import JobRun
from apps.core.serializers import JobRunSerializer

from .report import JOB_NAME, build, can_send, mask, render
from .tasks import weekly_report_task


@api_view(["GET"])
def report_status(request):
    last_run = JobRun.objects.filter(job=JOB_NAME).first()
    recipient = settings.REPORT_EMAIL_TO
    return Response(
        {
            "recipient": mask(recipient) if recipient else None,
            "schedule": {
                "day": settings.REPORT_DAY,
                "hour": settings.REPORT_HOUR,
                "minute": settings.REPORT_MINUTE,
            },
            "can_send": can_send(),
            "last_run": JobRunSerializer(last_run).data if last_run else None,
        }
    )


@require_GET
def preview(request):
    """The report as it would be sent now: HTML, or plain text with ?format=text.

    A plain Django view: DRF would treat ?format= as content negotiation."""
    subject, text, html = render(build(), request.GET.get("lang"))
    if request.GET.get("format") == "text":
        return HttpResponse(f"{subject}\n\n{text}", content_type="text/plain; charset=utf-8")
    return HttpResponse(html)


@api_view(["POST"])
def send_now(request):
    result = weekly_report_task.delay()
    return Response({"task_id": result.id}, status=status.HTTP_202_ACCEPTED)
