import hashlib
import hmac

from django.conf import settings


def create_razorpay_order(order):
    if settings.PAYMENT_STUB_MODE:
        return {
            "id": f"stub_order_{order.id}",
            "amount": int(order.total_amount * 100),
            "currency": "INR",
        }

    import razorpay

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return client.order.create(
        {
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "receipt": str(order.id),
        }
    )


def verify_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature or "")
