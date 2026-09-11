from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "order",
            "restaurant",
            "user_name",
            "rating",
            "comment",
            "restaurant_response",
            "responded_at",
            "created_at",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")


class ReviewRespondSerializer(serializers.Serializer):
    response = serializers.CharField(max_length=1000)
