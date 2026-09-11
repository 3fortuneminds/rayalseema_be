from django.urls import path

from .views import (
    PlatformDailySummaryView,
    PlatformDashboardView,
    RestaurantDashboardView,
    RestaurantSalesReportView,
)

app_name = "analytics"

urlpatterns = [
    path("restaurant/dashboard/", RestaurantDashboardView.as_view(), name="restaurant_dashboard"),
    path("restaurant/sales/", RestaurantSalesReportView.as_view(), name="restaurant_sales"),
    path("platform/dashboard/", PlatformDashboardView.as_view(), name="platform_dashboard"),
    path("platform/daily-summary/", PlatformDailySummaryView.as_view(), name="platform_daily_summary"),
]
