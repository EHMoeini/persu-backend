from django.urls import path

from .views import FacilityListView, MeView

app_name = "resources"

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("facilities", FacilityListView.as_view(), name="facility-list"),
]
