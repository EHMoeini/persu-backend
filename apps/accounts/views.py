"""Server-to-server authentication views."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApiError

from .authentication import BearerAuthentication
from .permissions import IsAuthenticatedUser
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    OtpVerifySerializer,
    PhoneSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import (
    InvalidCredentials,
    PhoneAlreadyRegistered,
    login_user,
    phone_exists,
    register_user,
)
from .throttles import AuthScopedRateThrottle
from .tokens import (
    InvalidRefreshToken,
    TokenPair,
    revoke_refresh_family,
    rotate_refresh_token,
)


def _token_response(
    user,
    pair: TokenPair,
    *,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {
            "accessToken": pair.access_token,
            "refreshToken": pair.refresh_token,
            "user": UserSerializer(user).data,
        },
        status=status_code,
    )


class PublicAuthView(APIView):
    """Base for public auth endpoints."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthScopedRateThrottle]


class CheckView(PublicAuthView):
    throttle_scope = "auth_check"

    def post(self, request) -> Response:
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"exists": phone_exists(serializer.validated_data["phone_e164"])}
        )


class LoginView(PublicAuthView):
    throttle_scope = "auth_login"

    def post(self, request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, pair = login_user(
                serializer.validated_data["phone_e164"],
                serializer.validated_data["password"],
            )
        except InvalidCredentials as exc:
            raise ApiError(
                "Invalid phone number or password.",
                code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        return _token_response(user, pair)


class RegisterView(PublicAuthView):
    throttle_scope = "auth_register"

    def post(self, request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, pair = register_user(
                serializer.validated_data["phone_e164"],
                serializer.validated_data["password"],
            )
        except PhoneAlreadyRegistered as exc:
            raise ApiError(
                "Phone number is already registered.",
                code="phone_already_registered",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

        return _token_response(user, pair, status_code=status.HTTP_201_CREATED)


class RefreshView(PublicAuthView):
    throttle_scope = "auth_refresh"

    def post(self, request) -> Response:
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pair = rotate_refresh_token(
                serializer.validated_data["refreshToken"]
            )
        except InvalidRefreshToken as exc:
            raise ApiError(
                "Invalid or expired refresh token.",
                code="invalid_refresh_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        return Response(
            {
                "accessToken": pair.access_token,
                "refreshToken": pair.refresh_token,
            }
        )


class LogoutView(PublicAuthView):
    throttle_scope = "auth_logout"

    def post(self, request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revoke_refresh_family(serializer.validated_data["refreshToken"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedUser]
    throttle_classes = []

    def get(self, request) -> Response:
        return Response({"user": UserSerializer(request.user).data})


class OtpSendView(PublicAuthView):
    throttle_scope = "auth_otp_send"

    def post(self, request) -> Response:
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True})


class OtpVerifyView(PublicAuthView):
    throttle_scope = "auth_otp_verify"

    def post(self, request) -> Response:
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True})
