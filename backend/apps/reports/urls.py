from django.urls import path

from . import views

urlpatterns = [
    path("reports/weekly/", views.report_status, name="report-status"),
    path("reports/weekly/preview/", views.preview, name="report-preview"),
    path("reports/weekly/send/", views.send_now, name="report-send"),
]
