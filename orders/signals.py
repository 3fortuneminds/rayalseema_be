from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from notifications.models import NotificationType
from notifications.services import notify_user
from tracking.services import broadcast_to_order

from .models import Order


@receiver(pre_save, sender=Order)
def _capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = Order.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def _broadcast_status_change(sender, instance, created, **kwargs):
    old_status = getattr(instance, "_old_status", None)
    if not created and old_status == instance.status:
        return

    broadcast_to_order(
        instance.id,
        {
            "type": "order.status",
            "status": instance.status,
            "payment_status": instance.payment_status,
            "updated_at": instance.updated_at.isoformat(),
        },
    )

    notify_user(
        instance.user,
        title=f"Order {instance.get_status_display()}",
        body=f"Your order from {instance.restaurant.name} is now {instance.get_status_display()}.",
        notification_type=NotificationType.ORDER_STATUS,
        related_order=instance,
    )
