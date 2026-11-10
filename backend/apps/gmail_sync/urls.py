from django.urls import path

from . import views

urlpatterns = [
    path("gmail/status/", views.gmail_status, name="gmail-status"),
    path("gmail/sync/", views.gmail_sync, name="gmail-sync"),
]
