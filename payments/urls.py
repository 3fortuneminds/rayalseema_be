from django.urls import path

from .views import CreatePaymentView, VerifyPaymentView

app_name = "payments"

urlpatterns = [
    path("create/", CreatePaymentView.as_view(), name="create"),
    path("verify/", VerifyPaymentView.as_view(), name="verify"),
]
