from django.urls import path

from .views import PushLocationView

app_name = "tracking"

urlpatterns = [
    path("location/", PushLocationView.as_view(), name="push_location"),
]
