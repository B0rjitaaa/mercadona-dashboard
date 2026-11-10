from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("jobs", views.JobRunViewSet, basename="job")

urlpatterns = [
    path("health/", views.health, name="health"),
    *router.urls,
]
