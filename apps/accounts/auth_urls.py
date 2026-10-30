from django.urls import path

from .views import (
    CheckView,
    LoginView,
    LogoutView,
    OtpSendView,
    OtpVerifyView,
    RefreshView,
    RegisterView,
    SessionView,
)

app_name = "auth"

urlpatterns = [
    path("check", CheckView.as_view(), name="check"),
    path("login", LoginView.as_view(), name="login"),
    path("register", RegisterView.as_view(), name="register"),
    path("refresh", RefreshView.as_view(), name="refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("session", SessionView.as_view(), name="session"),
    path("otp/send", OtpSendView.as_view(), name="otp-send"),
    path("otp/verify", OtpVerifyView.as_view(), name="otp-verify"),
]
