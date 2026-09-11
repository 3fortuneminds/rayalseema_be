from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from restaurants.models import Restaurant
from tracking.services import restaurant_group_name


class RestaurantOrderQueueConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.restaurant_id = self.scope["url_route"]["kwargs"]["restaurant_id"]
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        owns_restaurant = await self._owns_restaurant(self.restaurant_id, user)
        if not owns_restaurant:
            await self.close(code=4403)
            return

        self.group_name = restaurant_group_name(self.restaurant_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_new(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _owns_restaurant(self, restaurant_id, user):
        return Restaurant.objects.filter(id=restaurant_id, owner=user).exists()
