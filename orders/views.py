from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.mixins import EnvelopeMixin
from core.permissions import IsRestaurantOwner
from core.responses import error_response, success_response

from .models import Order, OrderStatus
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer
from .services import OrderError, create_order


class OrderViewSet(
    EnvelopeMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("restaurant").prefetch_related("items")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "list":
            return OrderListSerializer
        return OrderDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = create_order(
                user=request.user,
                address_id=serializer.validated_data["address_id"],
                items_data=serializer.validated_data["items"],
                coupon_code=serializer.validated_data.get("coupon_code"),
            )
        except OrderError as exc:
            return error_response(message=str(exc), status=400)

        return success_response(data=OrderDetailSerializer(order).data, message="Order placed", status=201)


class RestaurantOrderViewSet(
    EnvelopeMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get_queryset(self):
        return (
            Order.objects.filter(restaurant__owner=self.request.user)
            .select_related("restaurant", "user")
            .prefetch_related("items")
        )

    def get_serializer_class(self):
        return OrderListSerializer if self.action == "list" else OrderDetailSerializer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        order = self.get_object()
        if order.status != OrderStatus.PLACED:
            return error_response(message="Only newly placed orders can be accepted", status=400)
        order.status = OrderStatus.ACCEPTED
        order.save(update_fields=["status", "updated_at"])
        return success_response(data=OrderDetailSerializer(order).data, message="Order accepted")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        order = self.get_object()
        if order.status != OrderStatus.PLACED:
            return error_response(message="Only newly placed orders can be rejected", status=400)
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        return success_response(data=OrderDetailSerializer(order).data, message="Order rejected")

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        order = self.get_object()
        transitions = {
            OrderStatus.ACCEPTED: OrderStatus.PREPARING,
            OrderStatus.PREPARING: OrderStatus.OUT_FOR_DELIVERY,
        }
        next_status = transitions.get(order.status)
        if next_status is None:
            return error_response(message="Order cannot be advanced from its current status", status=400)
        order.status = next_status
        order.save(update_fields=["status", "updated_at"])
        return success_response(data=OrderDetailSerializer(order).data, message="Order status updated")
