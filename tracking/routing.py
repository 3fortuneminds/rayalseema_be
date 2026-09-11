from django.urls import re_path

from .consumers import OrderTrackingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/orders/(?P<order_id>[0-9a-fA-F-]+)/$", OrderTrackingConsumer.as_asgi()),
]
