from django.urls import re_path

from .consumers import UserNotificationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/notifications/$", UserNotificationConsumer.as_asgi()),
]
