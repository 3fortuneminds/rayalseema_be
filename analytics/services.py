from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User, UserRole
from delivery.models import DeliveryPartner
from orders.models import Order, OrderItem, OrderPaymentStatus, OrderStatus
from restaurants.models import Restaurant

from .models import PlatformDailySummary


def _paid_orders_qs(restaurant):
    return Order.objects.filter(restaurant=restaurant, payment_status=OrderPaymentStatus.PAID).exclude(
        status=OrderStatus.CANCELLED
    )


def get_dashboard_stats(restaurant):
    today = timezone.localdate()
    today_stats = _paid_orders_qs(restaurant).filter(placed_at__date=today).aggregate(
        count=Count("id"), revenue=Sum("total_amount")
    )

    since = timezone.now() - timedelta(days=30)
    top_items = (
        OrderItem.objects.filter(order__in=_paid_orders_qs(restaurant), order__placed_at__gte=since)
        .values("food_name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )

    return {
        "today_orders": today_stats["count"] or 0,
        "today_revenue": today_stats["revenue"] or 0,
        "top_items": list(top_items),
    }


def get_sales_report(restaurant, start_date, end_date):
    qs = _paid_orders_qs(restaurant).filter(placed_at__date__gte=start_date, placed_at__date__lte=end_date)
    daily = (
        qs.annotate(date=TruncDate("placed_at"))
        .values("date")
        .annotate(order_count=Count("id"), revenue=Sum("total_amount"))
        .order_by("date")
    )
    return list(daily)


def _all_paid_orders_qs():
    return Order.objects.filter(payment_status=OrderPaymentStatus.PAID).exclude(status=OrderStatus.CANCELLED)


def get_platform_dashboard():
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    paid = _all_paid_orders_qs()

    def summarize(qs):
        agg = qs.aggregate(count=Count("id"), revenue=Sum("total_amount"))
        return {"orders": agg["count"] or 0, "revenue": agg["revenue"] or 0}

    since14 = today - timedelta(days=13)
    volume = (
        paid.filter(placed_at__date__gte=since14)
        .annotate(date=TruncDate("placed_at"))
        .values("date")
        .annotate(order_count=Count("id"), revenue=Sum("total_amount"))
        .order_by("date")
    )

    return {
        "today": summarize(paid.filter(placed_at__date=today)),
        "this_week": summarize(paid.filter(placed_at__date__gte=week_start)),
        "this_month": summarize(paid.filter(placed_at__date__gte=month_start)),
        "all_time": summarize(paid),
        "active_customers": User.objects.filter(role=UserRole.CUSTOMER, is_active=True).count(),
        "active_restaurants": Restaurant.objects.filter(is_approved=True, is_active=True).count(),
        "active_delivery_partners": DeliveryPartner.objects.filter(is_approved=True, is_active=True).count(),
        "pending_restaurant_approvals": Restaurant.objects.filter(is_approved=False).count(),
        "pending_delivery_approvals": DeliveryPartner.objects.filter(is_approved=False).count(),
        "order_volume": list(volume),
    }


def get_platform_daily_summary(start_date, end_date):
    paid = _all_paid_orders_qs().filter(placed_at__date__gte=start_date, placed_at__date__lte=end_date)
    daily_orders = (
        paid.annotate(date=TruncDate("placed_at"))
        .values("date")
        .annotate(order_count=Count("id"), revenue=Sum("total_amount"))
        .order_by("date")
    )
    daily_customers = (
        User.objects.filter(role=UserRole.CUSTOMER, date_joined__date__gte=start_date, date_joined__date__lte=end_date)
        .annotate(date=TruncDate("date_joined"))
        .values("date")
        .annotate(count=Count("id"))
    )
    customers_by_date = {row["date"]: row["count"] for row in daily_customers}

    rows = []
    for row in daily_orders:
        summary, _ = PlatformDailySummary.objects.update_or_create(
            date=row["date"],
            defaults={
                "total_orders": row["order_count"],
                "total_revenue": row["revenue"] or 0,
                "new_customers": customers_by_date.get(row["date"], 0),
            },
        )
        rows.append(summary)
    return rows
