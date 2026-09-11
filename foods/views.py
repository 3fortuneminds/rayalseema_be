from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.mixins import EnvelopeMixin
from core.permissions import IsRestaurantOwner
from core.responses import success_response
from restaurants.models import Restaurant

from .models import Food, FoodCategory, FoodVariant, FoodWishlist
from .serializers import (
    FoodCategorySerializer,
    FoodCategoryWriteSerializer,
    FoodDetailSerializer,
    FoodListSerializer,
    FoodVariantWriteSerializer,
    FoodWriteSerializer,
)


class FoodCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = FoodCategory.objects.all()
        restaurant_slug = request.query_params.get("restaurant")
        if restaurant_slug:
            qs = qs.filter(restaurant__slug=restaurant_slug)
        return success_response(data=FoodCategorySerializer(qs, many=True).data)


class MyFoodCategoryViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    serializer_class = FoodCategoryWriteSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get_queryset(self):
        return FoodCategory.objects.filter(restaurant__owner=self.request.user)

    def perform_create(self, serializer):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if restaurant is None:
            raise PermissionDenied("You don't have a restaurant yet")
        serializer.save(restaurant=restaurant)


class FoodViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    filter_backends = [SearchFilter]
    search_fields = ["name", "description"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "toggle_availability"]:
            return [IsAuthenticated(), IsRestaurantOwner()]
        if self.action == "wishlist":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return FoodWriteSerializer
        return FoodDetailSerializer if self.action == "retrieve" else FoodListSerializer

    def get_queryset(self):
        if self.action in ["update", "partial_update", "destroy", "toggle_availability"]:
            return Food.objects.filter(restaurant__owner=self.request.user)

        if self.action == "list" and self.request.query_params.get("mine") == "true":
            if not self.request.user.is_authenticated:
                return Food.objects.none()
            return (
                Food.objects.filter(restaurant__owner=self.request.user)
                .select_related("restaurant", "category")
                .prefetch_related("variants")
            )

        qs = Food.objects.filter(is_available=True, restaurant__is_active=True, restaurant__is_approved=True)

        restaurant_slug = self.request.query_params.get("restaurant")
        if restaurant_slug:
            qs = qs.filter(restaurant__slug=restaurant_slug)

        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        is_vegetarian = self.request.query_params.get("is_vegetarian")
        if is_vegetarian is not None:
            qs = qs.filter(is_vegetarian=is_vegetarian.lower() == "true")

        return qs.select_related("restaurant", "category").prefetch_related("variants")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["wishlist_ids"] = set(FoodWishlist.objects.filter(user=user).values_list("food_id", flat=True))
        return context

    def perform_create(self, serializer):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if restaurant is None:
            raise PermissionDenied("You don't have a restaurant yet")
        serializer.save(restaurant=restaurant)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def wishlist(self, request, pk=None):
        food = self.get_object()
        FoodWishlist.objects.get_or_create(user=request.user, food=food)
        return success_response(message="Added to wishlist")

    @wishlist.mapping.delete
    def unwishlist(self, request, pk=None):
        food = self.get_object()
        FoodWishlist.objects.filter(user=request.user, food=food).delete()
        return success_response(message="Removed from wishlist")

    @action(detail=True, methods=["post"], url_path="toggle-availability")
    def toggle_availability(self, request, pk=None):
        food = self.get_object()
        food.is_available = not food.is_available
        food.save(update_fields=["is_available"])
        return success_response(data=FoodDetailSerializer(food).data, message="Availability updated")


class MyFoodVariantViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    serializer_class = FoodVariantWriteSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get_queryset(self):
        qs = FoodVariant.objects.filter(food__restaurant__owner=self.request.user)
        food_id = self.request.query_params.get("food")
        if food_id:
            qs = qs.filter(food_id=food_id)
        return qs

    def perform_create(self, serializer):
        food = serializer.validated_data["food"]
        if food.restaurant.owner_id != self.request.user.id:
            raise PermissionDenied("You don't own this food's restaurant")
        serializer.save()


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        foods = Food.objects.filter(wishlisted_by__user=request.user)
        serializer = FoodListSerializer(foods, many=True, context={"request": request})
        return success_response(data=serializer.data)
