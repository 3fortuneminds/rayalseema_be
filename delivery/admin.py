from django.contrib import admin

from .models import DeliveryAssignment, DeliveryPartner


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = ["user", "vehicle_type", "vehicle_number", "is_approved", "is_online"]
    list_editable = ["is_approved"]
    list_filter = ["vehicle_type", "is_approved", "is_online"]
    search_fields = ["user__email", "vehicle_number"]


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ["order", "delivery_partner", "status", "earning_amount", "assigned_at"]
    list_filter = ["status"]
    search_fields = ["order__id", "delivery_partner__user__email"]
