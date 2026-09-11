import uuid

from django.conf import settings
from django.db import models


class VehicleType(models.TextChoices):
    BIKE = "bike", "Bike"
    SCOOTER = "scooter", "Scooter"
    BICYCLE = "bicycle", "Bicycle"
    CAR = "car", "Car"


class DeliveryPartner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delivery_partner")

    vehicle_type = models.CharField(max_length=10, choices=VehicleType.choices, default=VehicleType.BIKE)
    vehicle_number = models.CharField(max_length=30, blank=True)
    license_number = models.CharField(max_length=30, blank=True)

    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_partners"

    def __str__(self):
        return f"{self.user.email} ({self.vehicle_type})"


class AssignmentStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    PICKED_UP = "picked_up", "Picked Up"
    DELIVERED = "delivered", "Delivered"


class DeliveryAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="delivery_assignment")
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.CASCADE, related_name="assignments")

    status = models.CharField(max_length=10, choices=AssignmentStatus.choices, default=AssignmentStatus.ASSIGNED)
    earning_amount = models.DecimalField(max_digits=8, decimal_places=2)

    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "delivery_assignments"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"Assignment for Order {self.order_id} -> {self.delivery_partner.user.email}"
