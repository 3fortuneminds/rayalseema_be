from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import error_response, success_response
from orders.models import Order, OrderPaymentStatus
from orders.serializers import OrderDetailSerializer

from .models import Payment, PaymentStatus
from .services import create_razorpay_order, verify_signature


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = Order.objects.filter(id=order_id, user=request.user).first()
        if order is None:
            return error_response(message="Order not found", status=404)

        if order.payment_status == OrderPaymentStatus.PAID:
            return error_response(message="Order is already paid", status=400)

        razorpay_order = create_razorpay_order(order)
        payment = Payment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order.get("id", ""),
            amount=order.total_amount,
            is_stub=settings.PAYMENT_STUB_MODE,
        )

        return success_response(
            data={
                "payment_id": str(payment.id),
                "razorpay_order_id": razorpay_order.get("id"),
                "amount": razorpay_order.get("amount"),
                "currency": razorpay_order.get("currency", "INR"),
                "key_id": settings.RAZORPAY_KEY_ID,
                "stub": settings.PAYMENT_STUB_MODE,
            }
        )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = Order.objects.filter(id=order_id, user=request.user).first()
        if order is None:
            return error_response(message="Order not found", status=404)

        payment = order.payments.filter(status=PaymentStatus.CREATED).order_by("-created_at").first()
        if payment is None:
            return error_response(message="No pending payment for this order", status=400)

        if settings.PAYMENT_STUB_MODE:
            payment.razorpay_payment_id = f"stub_pay_{payment.id}"
            payment.status = PaymentStatus.SUCCESS
            payment.save(update_fields=["razorpay_payment_id", "status", "updated_at"])
        else:
            razorpay_payment_id = request.data.get("razorpay_payment_id")
            razorpay_signature = request.data.get("razorpay_signature")

            if not verify_signature(payment.razorpay_order_id, razorpay_payment_id, razorpay_signature):
                payment.status = PaymentStatus.FAILED
                payment.save(update_fields=["status", "updated_at"])
                return error_response(message="Payment verification failed", status=400)

            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = PaymentStatus.SUCCESS
            payment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status", "updated_at"])

        order.payment_status = OrderPaymentStatus.PAID
        order.save(update_fields=["payment_status", "updated_at"])

        return success_response(data=OrderDetailSerializer(order).data, message="Payment successful")
