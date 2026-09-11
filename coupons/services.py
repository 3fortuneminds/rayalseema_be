from .models import Coupon, CouponUsage


class CouponError(Exception):
    pass


def validate_coupon(code, user, subtotal):
    coupon = Coupon.objects.filter(code__iexact=code).first()
    if coupon is None:
        raise CouponError("Invalid coupon code")

    if not coupon.is_valid_now():
        raise CouponError("Coupon has expired or is inactive")

    if subtotal < coupon.min_order_amount:
        raise CouponError(f"Minimum order amount is ₹{coupon.min_order_amount}")

    if coupon.usage_limit is not None and coupon.usages.count() >= coupon.usage_limit:
        raise CouponError("Coupon usage limit reached")

    if CouponUsage.objects.filter(coupon=coupon, user=user).count() >= coupon.per_user_limit:
        raise CouponError("You've already used this coupon")

    discount = coupon.compute_discount(subtotal)
    return coupon, discount
