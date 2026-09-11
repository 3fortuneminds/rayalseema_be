from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from restaurants.views import SearchView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/otp/", include("otp.urls")),
    path("api/v1/addresses/", include("addresses.urls")),
    path("api/v1/restaurants/", include("restaurants.urls")),
    path("api/v1/foods/", include("foods.urls")),
    path("api/v1/coupons/", include("coupons.urls")),
    path("api/v1/orders/", include("orders.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/tracking/", include("tracking.urls")),
    path("api/v1/reviews/", include("reviews.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/delivery/", include("delivery.urls")),
    path("api/v1/admin/", include("adminpanel.urls")),
    path("api/v1/search/", SearchView.as_view(), name="search"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
