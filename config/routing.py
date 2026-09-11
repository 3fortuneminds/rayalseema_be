from notifications.routing import websocket_urlpatterns as notifications_websocket_urlpatterns
from orders.routing import websocket_urlpatterns as orders_websocket_urlpatterns
from tracking.routing import websocket_urlpatterns as tracking_websocket_urlpatterns

websocket_urlpatterns = [
    *tracking_websocket_urlpatterns,
    *notifications_websocket_urlpatterns,
    *orders_websocket_urlpatterns,
]
