import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.renderers import JSONRenderer


def json_safe(data):
    """Round-trip through DRF's renderer so UUID/Decimal/datetime become
    plain str — Channels' send_json uses stdlib json, which chokes on the
    native Python types serializer.data leaves in place."""
    return json.loads(JSONRenderer().render(data))


def order_group_name(order_id):
    return f"order_{order_id}"


def broadcast_to_order(order_id, event):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(order_group_name(order_id), event)


def restaurant_group_name(restaurant_id):
    return f"restaurant_{restaurant_id}"


def broadcast_to_restaurant(restaurant_id, event):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(restaurant_group_name(restaurant_id), event)
