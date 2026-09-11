import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from .models import Notification, NotificationType

logger = logging.getLogger("notifications")


def user_group_name(user_id):
    return f"user_{user_id}"


def _broadcast_to_user(user_id, event):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(user_group_name(user_id), event)


def send_push_notification(user, title, body):
    if not settings.FIREBASE_CREDENTIALS_JSON:
        logger.info("[STUB] Push to %s: %s — %s", user.email, title, body)
        return
    # Real firebase-admin FCM send would go here once FIREBASE_CREDENTIALS_JSON
    # is configured with a real service account and device tokens are collected.


def notify_user(user, title, body, notification_type=NotificationType.SYSTEM, related_order=None):
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        related_order=related_order,
    )

    _broadcast_to_user(
        user.id,
        {
            "type": "notification.new",
            "id": str(notification.id),
            "title": notification.title,
            "body": notification.body,
            "notification_type": notification.notification_type,
            "related_order": str(related_order.id) if related_order else None,
            "is_read": False,
            "created_at": notification.created_at.isoformat(),
        },
    )
    send_push_notification(user, title, body)

    return notification
