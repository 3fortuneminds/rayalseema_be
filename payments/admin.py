from django.contrib import admin

from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "status", "is_stub", "created_at"]
    list_filter = ["status", "is_stub"]
    search_fields = ["order__id", "razorpay_order_id", "razorpay_payment_id"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["id", "payment", "amount", "processed_by", "created_at"]
    search_fields = ["payment__id"]
