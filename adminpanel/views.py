from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from accounts.models import User, UserRole
from core.mixins import EnvelopeMixin
from core.models import AuditLog
from core.pagination import StandardResultsPagination
from core.permissions import IsAdminRole
from core.responses import error_response, success_response
from core.services import log_action
from coupons.models import Coupon
from delivery.models import DeliveryPartner
from orders.models import Order, OrderPaymentStatus
from orders.serializers import OrderDetailSerializer, OrderListSerializer
from payments.models import Payment, Refund
from restaurants.models import Restaurant

from .models import PlatformSettings
from .serializers import (
    AdminCouponSerializer,
    AdminDeliveryPartnerSerializer,
    AdminPaymentSerializer,
    AdminRestaurantSerializer,
    AdminUserSerializer,
    AuditLogSerializer,
    CouponUsageSerializer,
    PlatformSettingsSerializer,
    RefundCreateSerializer,
)


class AdminUserViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminUserSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = User.objects.filter(role=UserRole.CUSTOMER).order_by("-date_joined")
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(email__icontains=search)
        return qs

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        log_action(request.user, "suspend_user", "user", user.id, {"email": user.email})
        return success_response(data=AdminUserSerializer(user).data, message="User suspended")

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        log_action(request.user, "reactivate_user", "user", user.id, {"email": user.email})
        return success_response(data=AdminUserSerializer(user).data, message="User reactivated")


class AdminRestaurantViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminRestaurantSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = Restaurant.objects.select_related("owner").order_by("-created_at")
        is_approved = self.request.query_params.get("is_approved")
        if is_approved is not None:
            qs = qs.filter(is_approved=is_approved.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        restaurant = self.get_object()
        restaurant.is_approved = True
        restaurant.save(update_fields=["is_approved"])
        log_action(request.user, "approve_restaurant", "restaurant", restaurant.id, {"name": restaurant.name})
        return success_response(data=AdminRestaurantSerializer(restaurant).data, message="Restaurant approved")

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        restaurant = self.get_object()
        restaurant.is_active = False
        restaurant.save(update_fields=["is_active"])
        log_action(request.user, "suspend_restaurant", "restaurant", restaurant.id, {"name": restaurant.name})
        return success_response(data=AdminRestaurantSerializer(restaurant).data, message="Restaurant suspended")

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        restaurant = self.get_object()
        restaurant.is_active = True
        restaurant.save(update_fields=["is_active"])
        log_action(request.user, "reactivate_restaurant", "restaurant", restaurant.id, {"name": restaurant.name})
        return success_response(data=AdminRestaurantSerializer(restaurant).data, message="Restaurant reactivated")


class AdminDeliveryPartnerViewSet(
    EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminDeliveryPartnerSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = DeliveryPartner.objects.select_related("user").order_by("-created_at")
        is_approved = self.request.query_params.get("is_approved")
        if is_approved is not None:
            qs = qs.filter(is_approved=is_approved.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        partner = self.get_object()
        partner.is_approved = True
        partner.save(update_fields=["is_approved"])
        log_action(request.user, "approve_delivery_partner", "delivery_partner", partner.id, {"email": partner.user.email})
        return success_response(data=AdminDeliveryPartnerSerializer(partner).data, message="Delivery partner approved")

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        partner = self.get_object()
        partner.is_active = False
        partner.is_online = False
        partner.save(update_fields=["is_active", "is_online"])
        log_action(request.user, "suspend_delivery_partner", "delivery_partner", partner.id, {"email": partner.user.email})
        return success_response(data=AdminDeliveryPartnerSerializer(partner).data, message="Delivery partner suspended")

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        partner = self.get_object()
        partner.is_active = True
        partner.save(update_fields=["is_active"])
        log_action(request.user, "reactivate_delivery_partner", "delivery_partner", partner.id, {"email": partner.user.email})
        return success_response(data=AdminDeliveryPartnerSerializer(partner).data, message="Delivery partner reactivated")


class AdminOrderViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = Order.objects.select_related("restaurant", "user").prefetch_related("items").order_by("-placed_at")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        return qs

    def get_serializer_class(self):
        return OrderListSerializer if self.action == "list" else OrderDetailSerializer


class AdminPaymentViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminPaymentSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return Payment.objects.select_related("order", "order__user").prefetch_related("refunds").order_by("-created_at")

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        payment = self.get_object()
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        already_refunded = sum((r.amount for r in payment.refunds.all()), start=0)
        if already_refunded + amount > payment.amount:
            return error_response(message="Refund amount exceeds the payment amount", status=400)

        Refund.objects.create(
            payment=payment,
            amount=amount,
            reason=serializer.validated_data.get("reason", ""),
            processed_by=request.user,
        )
        order = payment.order
        order.payment_status = OrderPaymentStatus.REFUNDED
        order.save(update_fields=["payment_status", "updated_at"])
        log_action(
            request.user,
            "issue_refund",
            "payment",
            payment.id,
            {"amount": str(amount), "order_id": str(order.id)},
        )
        payment.refresh_from_db()
        return success_response(data=AdminPaymentSerializer(payment).data, message="Refund issued")


class AdminCouponViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminCouponSerializer
    pagination_class = StandardResultsPagination
    queryset = Coupon.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        coupon = serializer.save()
        log_action(self.request.user, "create_coupon", "coupon", coupon.id, {"code": coupon.code})

    def perform_update(self, serializer):
        coupon = serializer.save()
        log_action(self.request.user, "update_coupon", "coupon", coupon.id, {"code": coupon.code})

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete_coupon", "coupon", instance.id, {"code": instance.code})
        instance.delete()

    @action(detail=True, methods=["get"])
    def usage(self, request, pk=None):
        coupon = self.get_object()
        usages = coupon.usages.select_related("user", "order").order_by("-used_at")
        return success_response(data=CouponUsageSerializer(usages, many=True).data)


class AuditLogViewSet(EnvelopeMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsPagination
    queryset = AuditLog.objects.select_related("actor").all()


class PlatformSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return success_response(data=PlatformSettingsSerializer(PlatformSettings.load()).data)

    def patch(self, request):
        settings_obj = PlatformSettings.load()
        serializer = PlatformSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, "update_platform_settings", "platform_settings", "", serializer.data)
        return success_response(data=serializer.data, message="Settings updated")
