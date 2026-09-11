from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    food_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    address_id = serializers.UUIDField()
    items = OrderItemInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Cart is empty")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "food", "variant", "food_name", "variant_name", "unit_price", "quantity", "line_total"]


class OrderListSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "status",
            "payment_status",
            "total_amount",
            "item_count",
            "placed_at",
        ]

    def get_item_count(self, obj):
        return sum(i.quantity for i in obj.items.all())


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    review = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="user.full_name", read_only=True)
    customer_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "subtotal",
            "delivery_fee",
            "discount_amount",
            "address_label",
            "address_line1",
            "address_line2",
            "address_city",
            "address_state",
            "address_postal_code",
            "latitude",
            "longitude",
            "items",
            "updated_at",
            "review",
            "customer_name",
            "customer_phone",
        ]

    def get_review(self, obj):
        review = getattr(obj, "review", None)
        if review is None:
            return None
        from reviews.serializers import ReviewSerializer

        return ReviewSerializer(review).data
