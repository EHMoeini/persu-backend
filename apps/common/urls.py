from django.urls import path

from .views import HealthView

app_name = "common"

urlpatterns = [
    path("healthz", HealthView.as_view(), name="healthz"),
]
