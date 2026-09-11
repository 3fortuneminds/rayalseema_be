from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCouponViewSet,
    AdminDeliveryPartnerViewSet,
    AdminOrderViewSet,
    AdminPaymentViewSet,
    AdminRestaurantViewSet,
    AdminUserViewSet,
    AuditLogViewSet,
    PlatformSettingsView,
)

app_name = "adminpanel"

router = DefaultRouter()
router.register("users", AdminUserViewSet, basename="admin-user")
router.register("restaurants", AdminRestaurantViewSet, basename="admin-restaurant")
router.register("delivery-partners", AdminDeliveryPartnerViewSet, basename="admin-delivery-partner")
router.register("orders", AdminOrderViewSet, basename="admin-order")
router.register("payments", AdminPaymentViewSet, basename="admin-payment")
router.register("coupons", AdminCouponViewSet, basename="admin-coupon")
router.register("audit-log", AuditLogViewSet, basename="admin-audit-log")

urlpatterns = [
    path("settings/", PlatformSettingsView.as_view(), name="settings"),
] + router.urls
