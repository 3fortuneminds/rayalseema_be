from django.urls import path

from .views import ValidateCouponView

app_name = "coupons"

urlpatterns = [
    path("validate/", ValidateCouponView.as_view(), name="validate"),
]
