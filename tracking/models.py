import uuid

from django.db import models

from orders.models import Order


class LocationUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="location_updates")

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "location_updates"
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"Location for Order {self.order_id} @ {self.recorded_at}"
