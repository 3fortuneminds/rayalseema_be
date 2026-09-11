from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FavoriteRestaurantListView,
    MyOpeningHoursView,
    MyRestaurantView,
    RestaurantCategoryListView,
    RestaurantRegisterView,
    RestaurantVerifyRegistrationView,
    RestaurantViewSet,
)

app_name = "restaurants"

router = DefaultRouter()
router.register("", RestaurantViewSet, basename="restaurant")

urlpatterns = [
    path("categories/", RestaurantCategoryListView.as_view(), name="categories"),
    path("favorites/", FavoriteRestaurantListView.as_view(), name="favorites"),
    path("register/", RestaurantRegisterView.as_view(), name="register"),
    path("verify-registration/", RestaurantVerifyRegistrationView.as_view(), name="verify_registration"),
    path("me/", MyRestaurantView.as_view(), name="me"),
    path("me/opening-hours/", MyOpeningHoursView.as_view(), name="my_opening_hours"),
] + router.urls
