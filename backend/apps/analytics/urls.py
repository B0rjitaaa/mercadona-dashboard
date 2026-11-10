from django.urls import path

from . import views

urlpatterns = [
    path("analytics/summary/", views.summary, name="analytics-summary"),
    path("analytics/monthly/", views.monthly, name="analytics-monthly"),
    path("analytics/overview/", views.overview, name="analytics-overview"),
    path("analytics/compare/", views.compare, name="analytics-compare"),
    path("analytics/top-items/", views.top_items, name="analytics-top-items"),
    path("analytics/items/", views.items, name="analytics-items"),
    path("analytics/items/detail/", views.item_detail, name="analytics-item-detail"),
    path(
        "analytics/products/<int:product_id>/",
        views.product_detail,
        name="analytics-product-detail",
    ),
    path("analytics/categories/", views.categories, name="analytics-categories"),
    path("analytics/prices/", views.price_watch, name="analytics-prices"),
]
