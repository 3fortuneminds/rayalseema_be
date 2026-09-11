from django.urls import path

from .views import SendOTPView, VerifyOTPView

app_name = "otp"

urlpatterns = [
    path("send/", SendOTPView.as_view(), name="send_otp"),
    path("verify/", VerifyOTPView.as_view(), name="verify_otp"),
]
