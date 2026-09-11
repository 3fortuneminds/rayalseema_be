from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User, UserRole
from orders.models import Order
from orders.serializers import OrderDetailSerializer

from .models import DeliveryAssignment, DeliveryPartner, VehicleType


class DeliveryPartnerRegisterSerializer(serializers.Serializer):
    # owner account
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # vehicle / KYC
    vehicle_type = serializers.ChoiceField(choices=VehicleType.choices)
    vehicle_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            phone_number=validated_data.get("phone_number", ""),
            role=UserRole.DELIVERY,
        )
        partner = DeliveryPartner.objects.create(
            user=user,
            vehicle_type=validated_data["vehicle_type"],
            vehicle_number=validated_data.get("vehicle_number", ""),
            license_number=validated_data.get("license_number", ""),
        )
        return user, partner


class DeliveryPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPartner
        fields = ["id", "vehicle_type", "vehicle_number", "license_number", "is_approved", "is_online"]
        read_only_fields = ["id", "is_approved"]


class AvailableOrderSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_city = serializers.CharField(source="restaurant.city", read_only=True)
    restaurant_latitude = serializers.DecimalField(
        source="restaurant.latitude", max_digits=9, decimal_places=6, read_only=True
    )
    restaurant_longitude = serializers.DecimalField(
        source="restaurant.longitude", max_digits=9, decimal_places=6, read_only=True
    )
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "restaurant_name",
            "restaurant_city",
            "restaurant_latitude",
            "restaurant_longitude",
            "address_city",
            "total_amount",
            "placed_at",
            "distance_km",
        ]

    def get_distance_km(self, obj):
        return getattr(obj, "_distance_km", None)


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    order = OrderDetailSerializer(read_only=True)

    class Meta:
        model = DeliveryAssignment
        fields = ["id", "order", "status", "earning_amount", "assigned_at", "picked_up_at", "delivered_at"]
        read_only_fields = fields
