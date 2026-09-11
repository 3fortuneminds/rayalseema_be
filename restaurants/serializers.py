from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User, UserRole

from .models import FavoriteRestaurant, OpeningHours, Restaurant, RestaurantCategory


class RestaurantCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantCategory
        fields = ["id", "name", "slug", "icon"]


class OpeningHoursSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = OpeningHours
        fields = ["weekday", "weekday_display", "opens_at", "closes_at", "is_closed"]


class RestaurantListSerializer(serializers.ModelSerializer):
    categories = RestaurantCategorySerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "slug",
            "city",
            "categories",
            "logo",
            "cover_image",
            "avg_rating",
            "rating_count",
            "is_favorited",
            "distance_km",
        ]

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        favorite_ids = self.context.get("favorite_ids")
        if favorite_ids is not None:
            return obj.id in favorite_ids
        return FavoriteRestaurant.objects.filter(user=request.user, restaurant=obj).exists()

    def get_distance_km(self, obj):
        return getattr(obj, "_distance_km", None)


class RestaurantDetailSerializer(RestaurantListSerializer):
    opening_hours = OpeningHoursSerializer(many=True, read_only=True)

    class Meta(RestaurantListSerializer.Meta):
        fields = RestaurantListSerializer.Meta.fields + [
            "description",
            "address_line",
            "latitude",
            "longitude",
            "opening_hours",
            "is_approved",
            "is_active",
        ]


class RestaurantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "name",
            "description",
            "city",
            "address_line",
            "latitude",
            "longitude",
            "logo",
            "cover_image",
            "categories",
        ]


class OpeningHoursInputSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    opens_at = serializers.TimeField(required=False, allow_null=True)
    closes_at = serializers.TimeField(required=False, allow_null=True)
    is_closed = serializers.BooleanField(default=False)


class RestaurantRegisterSerializer(serializers.Serializer):
    # owner account
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # restaurant profile
    restaurant_name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address_line = serializers.CharField(max_length=255, required=False, allow_blank=True)

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
            role=UserRole.RESTAURANT,
        )
        restaurant = Restaurant.objects.create(
            owner=user,
            name=validated_data["restaurant_name"],
            description=validated_data.get("description", ""),
            city=validated_data.get("city", ""),
            address_line=validated_data.get("address_line", ""),
            is_approved=False,
        )
        return user, restaurant
