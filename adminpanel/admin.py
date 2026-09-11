from django.contrib import admin

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ["commission_percent", "delivery_radius_km", "support_email", "support_phone", "updated_at"]
