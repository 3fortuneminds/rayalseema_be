from rest_framework import serializers

from .models import Food, FoodCategory, FoodVariant, FoodWishlist


class FoodVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodVariant
        fields = ["id", "name", "price", "is_default"]


class FoodCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "name", "display_order"]


class FoodCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "name", "display_order"]
        read_only_fields = ["id"]


class FoodListSerializer(serializers.ModelSerializer):
    is_wishlisted = serializers.SerializerMethodField()
    variants = FoodVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Food
        fields = [
            "id",
            "restaurant",
            "category",
            "name",
            "base_price",
            "image",
            "is_vegetarian",
            "is_available",
            "is_wishlisted",
            "variants",
        ]

    def get_is_wishlisted(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        wishlist_ids = self.context.get("wishlist_ids")
        if wishlist_ids is not None:
            return obj.id in wishlist_ids
        return FoodWishlist.objects.filter(user=request.user, food=obj).exists()


class FoodDetailSerializer(FoodListSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)

    class Meta(FoodListSerializer.Meta):
        fields = FoodListSerializer.Meta.fields + [
            "description",
            "restaurant_name",
            "restaurant_slug",
        ]


class FoodWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = ["id", "category", "name", "description", "base_price", "image", "is_vegetarian", "is_available"]
        read_only_fields = ["id"]


class FoodVariantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodVariant
        fields = ["id", "food", "name", "price", "is_default"]
        read_only_fields = ["id"]
