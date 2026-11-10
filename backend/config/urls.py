from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.receipts.urls")),
    path("api/", include("apps.gmail_sync.urls")),
    path("api/", include("apps.analytics.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.reports.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
