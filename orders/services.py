from decimal import Decimal

from django.conf import settings
from django.db import transaction

from addresses.models import Address
from coupons.models import CouponUsage
from coupons.services import CouponError, validate_coupon
from foods.models import Food, FoodVariant
from tracking.services import broadcast_to_restaurant, json_safe

from .models import Order, OrderItem


class OrderError(Exception):
    pass


@transaction.atomic
def create_order(user, address_id, items_data, coupon_code=None):
    address = Address.objects.filter(id=address_id, user=user).first()
    if address is None:
        raise OrderError("Address not found")

    if not items_data:
        raise OrderError("Cart is empty")

    restaurant = None
    order_items = []
    subtotal = Decimal("0")

    for item in items_data:
        food = Food.objects.select_related("restaurant").filter(id=item["food_id"], is_available=True).first()
        if food is None:
            raise OrderError("One of the items is no longer available")

        if restaurant is None:
            restaurant = food.restaurant
        elif restaurant.id != food.restaurant.id:
            raise OrderError("All items in an order must be from the same restaurant")

        unit_price = food.base_price
        variant = None
        variant_name = ""
        variant_id = item.get("variant_id")
        if variant_id:
            variant = FoodVariant.objects.filter(id=variant_id, food=food).first()
            if variant is None:
                raise OrderError("Invalid item variant")
            unit_price = variant.price
            variant_name = variant.name

        quantity = item["quantity"]
        line_total = unit_price * quantity
        subtotal += line_total

        order_items.append(
            {
                "food": food,
                "variant": variant,
                "food_name": food.name,
                "variant_name": variant_name,
                "unit_price": unit_price,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    coupon = None
    discount_amount = Decimal("0")
    if coupon_code:
        try:
            coupon, discount_amount = validate_coupon(coupon_code, user, subtotal)
        except CouponError as exc:
            raise OrderError(str(exc)) from exc

    delivery_fee = Decimal(str(settings.DELIVERY_FLAT_FEE))
    total_amount = subtotal + delivery_fee - discount_amount

    order = Order.objects.create(
        user=user,
        restaurant=restaurant,
        coupon=coupon,
        address_label=address.label,
        address_line1=address.line1,
        address_line2=address.line2,
        address_city=address.city,
        address_state=address.state,
        address_postal_code=address.postal_code,
        latitude=address.latitude,
        longitude=address.longitude,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )
    OrderItem.objects.bulk_create([OrderItem(order=order, **fields) for fields in order_items])

    if coupon:
        CouponUsage.objects.create(coupon=coupon, user=user, order=order)

    from .serializers import OrderListSerializer

    broadcast_to_restaurant(
        restaurant.id,
        {"type": "order.new", "order": json_safe(OrderListSerializer(order).data)},
    )

    return order
