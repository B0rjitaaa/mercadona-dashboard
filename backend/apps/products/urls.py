from django.urls import path

from . import views

urlpatterns = [
    path("review/", views.review_list, name="review-list"),
    path("review/link/", views.review_link, name="review-link"),
    path("review/unlink/", views.review_unlink, name="review-unlink"),
    path("review/manual/", views.review_manual, name="review-manual"),
    path("review/rematch/", views.review_rematch, name="review-rematch"),
    path("catalog/search/", views.catalog_search, name="catalog-search"),
    path("catalog/status/", views.catalog_status, name="catalog-status"),
    path("catalog/sync/", views.catalog_sync, name="catalog-sync"),
]
