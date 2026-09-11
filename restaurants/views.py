from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from accounts.models import User, UserRole
from accounts.serializers import VerifyRegistrationSerializer
from accounts.services import build_tokens, user_payload
from core.mixins import EnvelopeMixin
from core.permissions import IsRestaurantOwner
from core.responses import error_response, success_response
from otp.models import OTP, OTPChannel, OTPPurpose
from otp.services import OTPError, consume_otp, send_email_otp

from .models import FavoriteRestaurant, OpeningHours, Restaurant, RestaurantCategory
from .serializers import (
    OpeningHoursInputSerializer,
    OpeningHoursSerializer,
    RestaurantCategorySerializer,
    RestaurantDetailSerializer,
    RestaurantListSerializer,
    RestaurantRegisterSerializer,
    RestaurantWriteSerializer,
)
from .utils import haversine_km


class RestaurantCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = RestaurantCategory.objects.all()
        return success_response(data=RestaurantCategorySerializer(categories, many=True).data)


class RestaurantViewSet(EnvelopeMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ["name", "city", "description"]
    lookup_field = "slug"

    def get_serializer_class(self):
        return RestaurantDetailSerializer if self.action == "retrieve" else RestaurantListSerializer

    def get_queryset(self):
        qs = Restaurant.objects.filter(is_active=True, is_approved=True).prefetch_related(
            "categories", "opening_hours"
        )

        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(categories__slug=category_slug)

        min_rating = self.request.query_params.get("min_rating")
        if min_rating:
            qs = qs.filter(avg_rating__gte=min_rating)

        return qs.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favorite_ids"] = set(
                FavoriteRestaurant.objects.filter(user=user).values_list("restaurant_id", flat=True)
            )
        return context

    def list(self, request, *args, **kwargs):
        restaurants = list(self.filter_queryset(self.get_queryset()))

        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius_km = request.query_params.get("radius_km")

        if lat and lng:
            lat_f, lng_f = float(lat), float(lng)
            for r in restaurants:
                if r.latitude is not None and r.longitude is not None:
                    r._distance_km = round(haversine_km(lat_f, lng_f, float(r.latitude), float(r.longitude)), 2)
                else:
                    r._distance_km = None
            if radius_km:
                restaurants = [
                    r for r in restaurants if r._distance_km is not None and r._distance_km <= float(radius_km)
                ]

        ordering = request.query_params.get("ordering")
        if ordering == "rating":
            restaurants.sort(key=lambda r: r.avg_rating)
        elif ordering == "-rating":
            restaurants.sort(key=lambda r: r.avg_rating, reverse=True)
        elif ordering == "distance" and lat and lng:
            restaurants.sort(key=lambda r: (r._distance_km is None, r._distance_km))

        page = self.paginate_queryset(restaurants)
        serializer = self.get_serializer(page if page is not None else restaurants, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def favorite(self, request, slug=None):
        restaurant = self.get_object()
        FavoriteRestaurant.objects.get_or_create(user=request.user, restaurant=restaurant)
        return success_response(message="Added to favorites")

    @favorite.mapping.delete
    def unfavorite(self, request, slug=None):
        restaurant = self.get_object()
        FavoriteRestaurant.objects.filter(user=request.user, restaurant=restaurant).delete()
        return success_response(message="Removed from favorites")


class FavoriteRestaurantListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = Restaurant.objects.filter(favorited_by__user=request.user)
        serializer = RestaurantListSerializer(favorites, many=True, context={"request": request})
        return success_response(data=serializer.data)


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from foods.models import Food
        from foods.serializers import FoodListSerializer

        query = request.query_params.get("q", "").strip()
        if not query:
            return success_response(data={"restaurants": [], "foods": []})

        restaurants = Restaurant.objects.filter(is_active=True, is_approved=True).filter(
            Q(name__icontains=query) | Q(city__icontains=query)
        )[:10]

        foods = Food.objects.filter(
            is_available=True, restaurant__is_active=True, restaurant__is_approved=True
        ).filter(Q(name__icontains=query) | Q(description__icontains=query))[:10]

        return success_response(
            data={
                "restaurants": RestaurantListSerializer(restaurants, many=True, context={"request": request}).data,
                "foods": FoodListSerializer(foods, many=True, context={"request": request}).data,
            }
        )


class RestaurantRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RestaurantRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, restaurant = serializer.save()

        otp = OTP.create_for(identifier=user.email, channel=OTPChannel.EMAIL, purpose=OTPPurpose.REGISTER)
        send_email_otp(user.email, otp.code)

        return success_response(message="Registered. Verification code sent to email.", status=201)


class RestaurantVerifyRegistrationView(APIView):
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

        user = User.objects.filter(email__iexact=email, role=UserRole.RESTAURANT).first()
        if user is None:
            return error_response(message="User not found", status=404)

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        restaurant = Restaurant.objects.filter(owner=user).first()
        tokens = build_tokens(user)
        return success_response(
            data={
                **tokens,
                "user": user_payload(user),
                "restaurant": RestaurantDetailSerializer(restaurant).data if restaurant else None,
            },
            message="Verified",
        )


class MyRestaurantView(APIView):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant is None:
            return error_response(message="You don't have a restaurant yet", status=404)
        return success_response(data=RestaurantDetailSerializer(restaurant, context={"request": request}).data)

    def patch(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant is None:
            return error_response(message="You don't have a restaurant yet", status=404)

        serializer = RestaurantWriteSerializer(restaurant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(
            data=RestaurantDetailSerializer(restaurant, context={"request": request}).data,
            message="Restaurant updated",
        )


class MyOpeningHoursView(APIView):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def put(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant is None:
            return error_response(message="You don't have a restaurant yet", status=404)

        serializer = OpeningHoursInputSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        for entry in serializer.validated_data:
            OpeningHours.objects.update_or_create(
                restaurant=restaurant,
                weekday=entry["weekday"],
                defaults={
                    "opens_at": entry.get("opens_at"),
                    "closes_at": entry.get("closes_at"),
                    "is_closed": entry.get("is_closed", False),
                },
            )

        return success_response(
            data=OpeningHoursSerializer(restaurant.opening_hours.all(), many=True).data,
            message="Opening hours updated",
        )
