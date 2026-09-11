from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from orders.models import Order

from .services import order_group_name


class OrderTrackingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        order = await self._get_order(self.order_id, user)
        if order is None:
            await self.close(code=4404)
            return

        self.group_name = order_group_name(self.order_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        latest_location = await self._get_latest_location(order)
        await self.send_json(
            {
                "type": "snapshot",
                "status": order.status,
                "payment_status": order.payment_status,
                "location": latest_location,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status(self, event):
        await self.send_json(event)

    async def location_update(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _get_order(self, order_id, user):
        return Order.objects.filter(id=order_id, user=user).first()

    @database_sync_to_async
    def _get_latest_location(self, order):
        location = order.location_updates.first()
        if location is None:
            return None
        return {
            "latitude": str(location.latitude),
            "longitude": str(location.longitude),
            "recorded_at": location.recorded_at.isoformat(),
        }
