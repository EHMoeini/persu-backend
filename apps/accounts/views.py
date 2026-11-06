"""Server-to-server authentication views."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApiError
from apps.common.schema import error_response

from .authentication import BearerAuthentication
from .permissions import IsAuthenticatedUser
from .schema import (
    CheckResponseSerializer,
    SuccessResponseSerializer,
    TokenPairResponseSerializer,
    TokenPairWithUserResponseSerializer,
    UserResponseSerializer,
)
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

    @extend_schema(
        tags=["Authentication"],
        summary="Check whether a phone number is registered",
        description=(
            "Normalizes `countryCode` and `phone` to E.164 before looking up "
            "the user. Public endpoint, throttled at 10 requests per minute per "
            "normalized phone number or per client IP for invalid numbers."
        ),
        auth=[],
        request=PhoneSerializer,
        responses={
            200: OpenApiResponse(
                response=CheckResponseSerializer,
                description="Phone lookup completed.",
            ),
            400: error_response(
                "Invalid or missing phone fields (`validation_error`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def post(self, request) -> Response:
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"exists": phone_exists(serializer.validated_data["phone_e164"])}
        )


class LoginView(PublicAuthView):
    throttle_scope = "auth_login"

    @extend_schema(
        tags=["Authentication"],
        summary="Log in with a phone number and password",
        description=(
            "Returns a new access token, rotating refresh token, and public "
            "user payload. Login revokes the user's previous refresh-token "
            "family. Invalid credentials return a generic `401` response. "
            "Public endpoint, throttled at 5 requests per minute per normalized "
            "phone number."
        ),
        auth=[],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=TokenPairWithUserResponseSerializer,
                description="Authentication succeeded.",
            ),
            400: error_response(
                "Invalid or missing request fields (`validation_error`)."
            ),
            401: error_response(
                "Invalid phone number or password (`invalid_credentials`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
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

    @extend_schema(
        tags=["Authentication"],
        summary="Register a phone number and password",
        description=(
            "Creates a user after normalizing the phone number to E.164 and "
            "returns a new access token, rotating refresh token, and public "
            "user payload. Public endpoint, throttled at 5 requests per minute "
            "per normalized phone number."
        ),
        auth=[],
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=TokenPairWithUserResponseSerializer,
                description="User created and authenticated.",
            ),
            400: error_response(
                "Invalid or missing request fields (`validation_error`)."
            ),
            409: error_response(
                "Phone number is already registered "
                "(`phone_already_registered`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
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

    @extend_schema(
        tags=["Authentication"],
        summary="Rotate a refresh token",
        description=(
            "Consumes a refresh token and returns a new access token and "
            "refresh token. Reusing a revoked token revokes the whole token "
            "family. Public endpoint, throttled at 20 requests per minute per "
            "refresh token."
        ),
        auth=[],
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                response=TokenPairResponseSerializer,
                description="Refresh token rotated successfully.",
            ),
            400: error_response(
                "Missing or blank refresh token (`validation_error`)."
            ),
            401: error_response(
                "Invalid, expired, revoked, or reused refresh token "
                "(`invalid_refresh_token`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
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

    @extend_schema(
        tags=["Authentication"],
        summary="Revoke a refresh-token family",
        description=(
            "Revokes the refresh-token family associated with the supplied "
            "refresh token. The operation is idempotent: unknown or "
            "already-revoked tokens also return `204`. Access tokens remain "
            "valid until they expire. Public endpoint, throttled at 30 requests "
            "per minute per refresh token."
        ),
        auth=[],
        request=LogoutSerializer,
        responses={
            204: OpenApiResponse(
                description="Refresh-token family revoked; empty response body.",
            ),
            400: error_response(
                "Missing or blank refresh token (`validation_error`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def post(self, request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revoke_refresh_family(serializer.validated_data["refreshToken"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedUser]
    throttle_classes = []

    @extend_schema(
        tags=["Authentication"],
        summary="Get the authenticated session user",
        description=(
            "Returns the public user payload identified by the Bearer access "
            "token. Requires an active authenticated user. Optional `nickName` "
            "and `avatar` fields are omitted when empty."
        ),
        responses={
            200: OpenApiResponse(
                response=UserResponseSerializer,
                description="Authenticated user returned.",
            ),
            401: error_response(
                "Missing, invalid, expired, or inactive-user access token "
                "(`unauthorized`)."
            ),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def get(self, request) -> Response:
        return Response({"user": UserSerializer(request.user).data})


class OtpSendView(PublicAuthView):
    throttle_scope = "auth_otp_send"

    @extend_schema(
        tags=["Authentication"],
        summary="Send an OTP (stub)",
        description=(
            "Validates the phone fields and returns success without sending an "
            "SMS. Public endpoint, throttled at 5 requests per minute per "
            "normalized phone number."
        ),
        auth=[],
        request=PhoneSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="OTP send stub completed.",
            ),
            400: error_response(
                "Invalid or missing phone fields (`validation_error`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def post(self, request) -> Response:
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True})


class OtpVerifyView(PublicAuthView):
    throttle_scope = "auth_otp_verify"

    @extend_schema(
        tags=["Authentication"],
        summary="Verify an OTP (stub)",
        description=(
            "Validates the phone fields and returns success. `code` is "
            "optional and currently ignored by the stub. Public endpoint, "
            "throttled at 10 requests per minute per normalized phone number."
        ),
        auth=[],
        request=OtpVerifySerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="OTP verify stub completed.",
            ),
            400: error_response(
                "Invalid or missing phone fields (`validation_error`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            429: error_response("Rate limit exceeded (`rate_limited`)."),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def post(self, request) -> Response:
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True})
