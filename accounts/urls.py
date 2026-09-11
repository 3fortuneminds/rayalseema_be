from django.urls import path

from .views import (
    ForgotPasswordView,
    GoogleLoginView,
    ProfileView,
    RegisterView,
    ResetPasswordView,
    RoleTokenObtainPairView,
    RoleTokenRefreshView,
    VerifyRegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-registration/", VerifyRegistrationView.as_view(), name="verify_registration"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", RoleTokenRefreshView.as_view(), name="token_refresh"),
]
