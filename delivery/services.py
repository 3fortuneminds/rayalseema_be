from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from .models import AssignmentStatus, DeliveryAssignment


def _summarize(qs):
    agg = qs.aggregate(count=Count("id"), total=Sum("earning_amount"))
    return {"deliveries": agg["count"] or 0, "earnings": agg["total"] or 0}


def get_earnings_summary(partner):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    delivered = DeliveryAssignment.objects.filter(delivery_partner=partner, status=AssignmentStatus.DELIVERED)

    return {
        "today": _summarize(delivered.filter(delivered_at__date=today)),
        "this_week": _summarize(delivered.filter(delivered_at__date__gte=week_start)),
        "all_time": _summarize(delivered),
    }
