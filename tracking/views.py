from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import error_response, success_response
from orders.models import Order

from .serializers import LocationUpdateSerializer
from .services import broadcast_to_order


class PushLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = Order.objects.filter(id=order_id).first()
        if order is None:
            return error_response(message="Order not found", status=404)

        from delivery.models import DeliveryAssignment

        is_assigned_partner = DeliveryAssignment.objects.filter(
            order=order, delivery_partner__user=request.user
        ).exists()
        if not (request.user.is_staff or is_assigned_partner):
            return error_response(
                message="Only the assigned delivery partner (or staff) can push location for this order",
                status=403,
            )

        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = serializer.save(order=order)

        broadcast_to_order(
            order.id,
            {
                "type": "location.update",
                "latitude": str(location.latitude),
                "longitude": str(location.longitude),
                "recorded_at": location.recorded_at.isoformat(),
            },
        )

        return success_response(message="Location pushed")
