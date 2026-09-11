from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptDeliveryView,
    AvailableOrdersView,
    DeliveryPartnerRegisterView,
    DeliveryPartnerVerifyRegistrationView,
    EarningsSummaryView,
    MyDeliveryPartnerView,
    MyDeliveryViewSet,
    ToggleOnlineView,
)

app_name = "delivery"

router = DefaultRouter()
router.register("my-deliveries", MyDeliveryViewSet, basename="my-delivery")

urlpatterns = [
    path("register/", DeliveryPartnerRegisterView.as_view(), name="register"),
    path("verify-registration/", DeliveryPartnerVerifyRegistrationView.as_view(), name="verify_registration"),
    path("me/", MyDeliveryPartnerView.as_view(), name="me"),
    path("me/toggle-online/", ToggleOnlineView.as_view(), name="toggle_online"),
    path("available-orders/", AvailableOrdersView.as_view(), name="available_orders"),
    path("available-orders/<uuid:order_id>/accept/", AcceptDeliveryView.as_view(), name="accept_delivery"),
    path("earnings/summary/", EarningsSummaryView.as_view(), name="earnings_summary"),
] + router.urls
