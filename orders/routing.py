from django.urls import re_path

from .consumers import RestaurantOrderQueueConsumer

websocket_urlpatterns = [
    re_path(r"^ws/restaurants/(?P<restaurant_id>[0-9a-fA-F-]+)/orders/$", RestaurantOrderQueueConsumer.as_asgi()),
]
