from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from accounts.models import User, UserRole
from accounts.serializers import VerifyRegistrationSerializer
from accounts.services import build_tokens, user_payload
from core.mixins import EnvelopeMixin
from core.permissions import IsDeliveryPartner
from core.responses import error_response, success_response
from orders.models import Order, OrderStatus
from otp.models import OTP, OTPChannel, OTPPurpose
from otp.services import OTPError, consume_otp, send_email_otp
from restaurants.utils import haversine_km

from .models import AssignmentStatus, DeliveryAssignment, DeliveryPartner
from .serializers import (
    AvailableOrderSerializer,
    DeliveryAssignmentSerializer,
    DeliveryPartnerRegisterSerializer,
    DeliveryPartnerSerializer,
)
from .services import get_earnings_summary


class DeliveryPartnerRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DeliveryPartnerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, partner = serializer.save()

        otp = OTP.create_for(identifier=user.email, channel=OTPChannel.EMAIL, purpose=OTPPurpose.REGISTER)
        send_email_otp(user.email, otp.code)

        return success_response(message="Registered. Verification code sent to email.", status=201)


class DeliveryPartnerVerifyRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            consume_otp(identifier=email, purpose=OTPPurpose.REGISTER, code=code)
        except OTPError as exc:
            return error_response(message=str(exc), status=400)

        user = User.objects.filter(email__iexact=email, role=UserRole.DELIVERY).first()
        if user is None:
            return error_response(message="User not found", status=404)

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        partner = DeliveryPartner.objects.filter(user=user).first()
        tokens = build_tokens(user)
        return success_response(
            data={
                **tokens,
                "user": user_payload(user),
                "partner": DeliveryPartnerSerializer(partner).data if partner else None,
            },
            message="Verified",
        )


class MyDeliveryPartnerView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPartner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        partner = DeliveryPartner.objects.filter(user=request.user).first()
        if partner is None:
            return error_response(message="Delivery partner profile not found", status=404)
        return success_response(data=DeliveryPartnerSerializer(partner).data)

    def patch(self, request):
        partner = DeliveryPartner.objects.filter(user=request.user).first()
        if partner is None:
            return error_response(message="Delivery partner profile not found", status=404)
        serializer = DeliveryPartnerSerializer(partner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Profile updated")


class ToggleOnlineView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPartner]

    def post(self, request):
        partner = DeliveryPartner.objects.filter(user=request.user).first()
        if partner is None:
            return error_response(message="Delivery partner profile not found", status=404)
        if not partner.is_approved:
            return error_response(message="Your account is pending approval", status=403)
        partner.is_online = not partner.is_online
        partner.save(update_fields=["is_online"])
        return success_response(data=DeliveryPartnerSerializer(partner).data, message="Availability updated")


class AvailableOrdersView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPartner]

    def get(self, request):
        orders = list(
            Order.objects.filter(status=OrderStatus.OUT_FOR_DELIVERY, delivery_assignment__isnull=True)
            .select_related("restaurant")
        )

        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        for o in orders:
            o._distance_km = None
        if lat and lng:
            lat_f, lng_f = float(lat), float(lng)
            for o in orders:
                if o.restaurant.latitude is not None and o.restaurant.longitude is not None:
                    o._distance_km = round(
                        haversine_km(lat_f, lng_f, float(o.restaurant.latitude), float(o.restaurant.longitude)), 2
                    )
            orders.sort(key=lambda o: (o._distance_km is None, o._distance_km))

        return success_response(data=AvailableOrderSerializer(orders, many=True).data)


class AcceptDeliveryView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPartner]

    def post(self, request, order_id):
        partner = DeliveryPartner.objects.filter(user=request.user, is_approved=True).first()
        if partner is None:
            return error_response(message="Your account is pending approval", status=403)

        order = Order.objects.filter(id=order_id, status=OrderStatus.OUT_FOR_DELIVERY).first()
        if order is None:
            return error_response(message="Order not available", status=404)

        if DeliveryAssignment.objects.filter(order=order).exists():
            return error_response(message="This order has already been claimed", status=409)

        assignment = DeliveryAssignment.objects.create(
            order=order,
            delivery_partner=partner,
            earning_amount=Decimal(str(settings.DELIVERY_PARTNER_EARNING_PER_ORDER)),
        )
        return success_response(
            data=DeliveryAssignmentSerializer(assignment).data, message="Delivery accepted", status=201
        )


class MyDeliveryViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DeliveryAssignmentSerializer
    permission_classes = [IsAuthenticated, IsDeliveryPartner]

    def get_queryset(self):
        return DeliveryAssignment.objects.filter(delivery_partner__user=self.request.user).select_related(
            "order", "order__restaurant", "order__user"
        )

    @action(detail=True, methods=["post"], url_path="picked-up")
    def picked_up(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status != AssignmentStatus.ASSIGNED:
            return error_response(message="Order must be assigned before pickup", status=400)
        assignment.status = AssignmentStatus.PICKED_UP
        assignment.picked_up_at = timezone.now()
        assignment.save(update_fields=["status", "picked_up_at"])
        return success_response(data=DeliveryAssignmentSerializer(assignment).data, message="Marked picked up")

    @action(detail=True, methods=["post"])
    def delivered(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status != AssignmentStatus.PICKED_UP:
            return error_response(message="Order must be picked up before marking delivered", status=400)
        assignment.status = AssignmentStatus.DELIVERED
        assignment.delivered_at = timezone.now()
        assignment.save(update_fields=["status", "delivered_at"])

        order = assignment.order
        order.status = OrderStatus.DELIVERED
        order.save(update_fields=["status", "updated_at"])

        return success_response(data=DeliveryAssignmentSerializer(assignment).data, message="Marked delivered")


class EarningsSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPartner]

    def get(self, request):
        partner = DeliveryPartner.objects.filter(user=request.user).first()
        if partner is None:
            return error_response(message="Delivery partner profile not found", status=404)
        return success_response(data=get_earnings_summary(partner))
