from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.responses import error_response, success_response

from .models import OTP, OTPChannel
from .serializers import SendOTPSerializer, VerifyOTPSerializer
from .services import OTPError, consume_otp, send_email_otp, send_sms_otp


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        channel = serializer.validated_data["channel"]
        purpose = serializer.validated_data["purpose"]

        otp = OTP.create_for(identifier=identifier, channel=channel, purpose=purpose)

        if channel == OTPChannel.EMAIL:
            send_email_otp(identifier, otp.code)
        else:
            send_sms_otp(identifier, otp.code)

        return success_response(message="OTP sent")


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        purpose = serializer.validated_data["purpose"]
        code = serializer.validated_data["code"]

        try:
            consume_otp(identifier=identifier, purpose=purpose, code=code)
        except OTPError as exc:
            return error_response(message=str(exc), status=400)

        return success_response(message="OTP verified")
