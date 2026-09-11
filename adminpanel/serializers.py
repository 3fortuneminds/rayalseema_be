from rest_framework import serializers

from accounts.models import User
from coupons.models import Coupon, CouponUsage
from core.models import AuditLog
from delivery.models import DeliveryPartner
from payments.models import Payment, Refund
from restaurants.models import Restaurant

from .models import PlatformSettings


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone_number", "role", "is_verified", "is_active", "date_joined"]
        read_only_fields = fields


class AdminRestaurantSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "slug",
            "city",
            "owner_email",
            "avg_rating",
            "rating_count",
            "is_approved",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class AdminDeliveryPartnerSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = DeliveryPartner
        fields = [
            "id",
            "user_email",
            "user_full_name",
            "vehicle_type",
            "vehicle_number",
            "license_number",
            "is_approved",
            "is_active",
            "is_online",
            "created_at",
        ]
        read_only_fields = fields


class AdminPaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source="order.id", read_only=True)
    customer_email = serializers.CharField(source="order.user.email", read_only=True)
    refunded_amount = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_id",
            "customer_email",
            "amount",
            "status",
            "is_stub",
            "refunded_amount",
            "created_at",
        ]
        read_only_fields = fields

    def get_refunded_amount(self, obj):
        return sum((r.amount for r in obj.refunds.all()), start=0)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "payment", "amount", "reason", "processed_by", "created_at"]
        read_only_fields = fields


class RefundCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AdminCouponSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "min_order_amount",
            "usage_limit",
            "per_user_limit",
            "valid_from",
            "valid_until",
            "is_active",
            "usage_count",
            "created_at",
        ]
        read_only_fields = ["id", "usage_count", "created_at"]

    def get_usage_count(self, obj):
        return obj.usages.count()


class CouponUsageSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    order_id = serializers.UUIDField(source="order.id", read_only=True)

    class Meta:
        model = CouponUsage
        fields = ["id", "user_email", "order_id", "used_at"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "actor_email", "action", "target_type", "target_id", "metadata", "created_at"]
        read_only_fields = fields


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ["commission_percent", "delivery_radius_km", "support_email", "support_phone", "updated_at"]
        read_only_fields = ["updated_at"]
