from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import error_response, success_response

from .serializers import ValidateCouponSerializer
from .services import CouponError, validate_coupon


class ValidateCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            coupon, discount = validate_coupon(
                serializer.validated_data["code"], request.user, serializer.validated_data["subtotal"]
            )
        except CouponError as exc:
            return error_response(message=str(exc), status=400)

        return success_response(
            data={
                "code": coupon.code,
                "description": coupon.description,
                "discount_amount": discount,
            }
        )
