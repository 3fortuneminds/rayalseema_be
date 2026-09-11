from django.contrib import admin

from .models import LocationUpdate


@admin.register(LocationUpdate)
class LocationUpdateAdmin(admin.ModelAdmin):
    list_display = ["order", "latitude", "longitude", "recorded_at"]
    search_fields = ["order__id"]
