from django.urls import path

from . import views

urlpatterns = [
    path("analytics/summary/", views.summary, name="analytics-summary"),
    path("analytics/monthly/", views.monthly, name="analytics-monthly"),
    path("analytics/top-items/", views.top_items, name="analytics-top-items"),
    path("analytics/items/", views.items, name="analytics-items"),
    path("analytics/items/detail/", views.item_detail, name="analytics-item-detail"),
]
