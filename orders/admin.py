from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "restaurant", "status", "payment_status", "total_amount", "placed_at"]
    list_editable = ["status"]
    list_filter = ["status", "payment_status"]
    search_fields = ["user__email", "id"]
    inlines = [OrderItemInline]
