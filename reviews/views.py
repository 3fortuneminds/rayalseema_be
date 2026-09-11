from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from core.mixins import EnvelopeMixin
from core.permissions import IsRestaurantOwner
from core.responses import error_response, success_response

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewRespondSerializer, ReviewSerializer
from .services import ReviewError, create_review


class ReviewViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action == "respond":
            return [IsAuthenticated(), IsRestaurantOwner()]
        return [AllowAny()]

    def get_serializer_class(self):
        return ReviewCreateSerializer if self.action == "create" else ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.select_related("user", "restaurant")
        restaurant_slug = self.request.query_params.get("restaurant")
        if restaurant_slug:
            qs = qs.filter(restaurant__slug=restaurant_slug)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = create_review(request.user, **serializer.validated_data)
        except ReviewError as exc:
            return error_response(message=str(exc), status=400)

        return success_response(data=ReviewSerializer(review).data, message="Review submitted", status=201)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        review = self.get_object()
        if review.restaurant.owner_id != request.user.id:
            return error_response(message="You can only respond to reviews of your own restaurant", status=403)

        serializer = ReviewRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review.restaurant_response = serializer.validated_data["response"]
        review.responded_at = timezone.now()
        review.save(update_fields=["restaurant_response", "responded_at"])

        return success_response(data=ReviewSerializer(review).data, message="Response submitted")
