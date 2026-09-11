from decimal import Decimal

from django.db.models import Avg, Count

from orders.models import Order, OrderStatus

from .models import Review


class ReviewError(Exception):
    pass


def create_review(user, order_id, rating, comment=""):
    order = Order.objects.filter(id=order_id, user=user).select_related("restaurant").first()
    if order is None:
        raise ReviewError("Order not found")

    if order.status != OrderStatus.DELIVERED:
        raise ReviewError("You can only review delivered orders")

    if hasattr(order, "review"):
        raise ReviewError("You've already reviewed this order")

    review = Review.objects.create(
        user=user, order=order, restaurant=order.restaurant, rating=rating, comment=comment
    )

    restaurant = order.restaurant
    agg = Review.objects.filter(restaurant=restaurant).aggregate(avg=Avg("rating"), count=Count("id"))
    restaurant.avg_rating = round(Decimal(agg["avg"]), 2)
    restaurant.rating_count = agg["count"]
    restaurant.save(update_fields=["avg_rating", "rating_count"])

    return review
