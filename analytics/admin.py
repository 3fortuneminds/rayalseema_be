from django.contrib import admin

from .models import PlatformDailySummary


@admin.register(PlatformDailySummary)
class PlatformDailySummaryAdmin(admin.ModelAdmin):
    list_display = ["date", "total_orders", "total_revenue", "new_customers"]
    ordering = ["-date"]
