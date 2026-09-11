from django.conf import settings
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from core.responses import error_response, success_response
from otp.models import OTP, OTPChannel, OTPPurpose
from otp.services import OTPError, consume_otp, send_email_otp

from .models import User, UserRole
from .serializers import (
    ForgotPasswordSerializer,
    GoogleAuthSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleTokenObtainPairSerializer,
    VerifyRegistrationSerializer,
)
from .services import build_tokens, user_payload


class RoleTokenObtainPairView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RoleTokenObtainPairSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return success_response(data=serializer.validated_data, message="Logged in")


class RoleTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(data=serializer.validated_data, message="Token refreshed")


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = OTP.create_for(identifier=user.email, channel=OTPChannel.EMAIL, purpose=OTPPurpose.REGISTER)
        send_email_otp(user.email, otp.code)

        return success_response(message="Registered. Verification code sent to email.", status=201)


class VerifyRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            consume_otp(identifier=email, purpose=OTPPurpose.REGISTER, code=code)
        except OTPError as exc:
            return error_response(message=str(exc), status=400)

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return error_response(message="User not found", status=404)

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        tokens = build_tokens(user)
        return success_response(data={**tokens, "user": user_payload(user)}, message="Verified")


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            otp = OTP.create_for(identifier=email, channel=OTPChannel.EMAIL, purpose=OTPPurpose.PASSWORD_RESET)
            send_email_otp(email, otp.code)

        return success_response(message="If that account exists, a reset code has been sent.")


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        try:
            consume_otp(identifier=email, purpose=OTPPurpose.PASSWORD_RESET, code=code)
        except OTPError as exc:
            return error_response(message=str(exc), status=400)

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return error_response(message="User not found", status=404)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return success_response(message="Password reset successful")


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["id_token"]

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except ValueError:
            return error_response(message="Invalid Google token", status=400)

        email = idinfo["email"]
        full_name = idinfo.get("name", "")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=None,
                full_name=full_name,
                role=UserRole.CUSTOMER,
                is_verified=True,
            )
        elif not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])

        tokens = build_tokens(user)
        return success_response(data={**tokens, "user": user_payload(user)}, message="Logged in with Google")


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Profile updated")
