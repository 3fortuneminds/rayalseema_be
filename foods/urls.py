from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import FoodCategoryListView, FoodViewSet, MyFoodCategoryViewSet, MyFoodVariantViewSet, WishlistView

app_name = "foods"

router = DefaultRouter()
router.register("", FoodViewSet, basename="food")

# SimpleRouter (not DefaultRouter) — a second DefaultRouter would add its own
# API-root view at "^$", which shadows FoodViewSet's own list route once the
# two url lists are concatenated.
my_router = SimpleRouter()
my_router.register("my-categories", MyFoodCategoryViewSet, basename="my-food-category")
my_router.register("my-variants", MyFoodVariantViewSet, basename="my-food-variant")

urlpatterns = (
    [
        path("categories/", FoodCategoryListView.as_view(), name="categories"),
        path("wishlist/", WishlistView.as_view(), name="wishlist"),
    ]
    + my_router.urls
    + router.urls
)
