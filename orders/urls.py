from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import OrderViewSet, RestaurantOrderViewSet

app_name = "orders"

router = DefaultRouter()
router.register("", OrderViewSet, basename="order")

# SimpleRouter (not DefaultRouter) — a second DefaultRouter would add its own
# API-root view at "^$", which shadows OrderViewSet's own list route once the
# two url lists are concatenated.
restaurant_router = SimpleRouter()
restaurant_router.register("restaurant", RestaurantOrderViewSet, basename="restaurant-order")

urlpatterns = restaurant_router.urls + router.urls
