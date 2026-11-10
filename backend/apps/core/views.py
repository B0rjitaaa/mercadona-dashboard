from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import JobRun
from .serializers import JobRunSerializer


@api_view(["GET"])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


class JobRunViewSet(viewsets.ReadOnlyModelViewSet):
    """Background job runs. Filter with ?job=sync_gmail."""

    serializer_class = JobRunSerializer

    def get_queryset(self):
        qs = JobRun.objects.all()
        if job := self.request.query_params.get("job"):
            qs = qs.filter(job=job)
        return qs
