"""Server-to-server authentication views."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
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
    InvalidOtpCode,
    PhoneAlreadyRegistered,
    login_user,
    phone_exists,
    register_user,
    verify_otp,
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
            "normalized phone number or per client IP for invalid numbers.\n\n"
            "Iran example: `countryCode=IR` with `phone=09123456789` "
            "normalizes to `+989123456789`."
        ),
        auth=[],
        request=PhoneSerializer,
        examples=[
            OpenApiExample(
                "Iran national number",
                value={"countryCode": "IR", "phone": "09123456789"},
                description=(
                    "The Iranian national number 09123456789 is normalized to "
                    "+989123456789 before the lookup."
                ),
                request_only=True,
            ),
            OpenApiExample(
                "Iran national number response",
                value={"exists": True},
                description=(
                    "Response when `IR` + `09123456789` belongs to the account "
                    "stored as `+989123456789`."
                ),
                response_only=True,
            ),
        ],
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
        examples=[
            OpenApiExample(
                "Iran national number",
                value={
                    "countryCode": "IR",
                    "phone": "09123456789",
                    "password": "correct horse battery staple",
                },
                description=(
                    "`09123456789` is normalized to `+989123456789` before "
                    "authentication."
                ),
                request_only=True,
            ),
            OpenApiExample(
                "Iran national number response",
                value={
                    "accessToken": "<access JWT>",
                    "refreshToken": "<opaque refresh token>",
                    "user": {
                        "id": "8d9a1f2b-3c4d-4e5f-8a6b-7c8d9e0f1a2b",
                        "phone": "+989123456789",
                    },
                },
                description=(
                    "The response `phone` is always E.164, even when the "
                    "request used the national form `09123456789`."
                ),
                response_only=True,
            ),
        ],
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
            "user payload. The optional `fullName` field is stored as the "
            "profile nickname and returned as `nickName`. Public endpoint, "
            "throttled at 5 requests per minute per normalized phone number."
        ),
        auth=[],
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                "Iran national number with full name",
                value={
                    "countryCode": "IR",
                    "phone": "09123456789",
                    "password": "correct horse battery staple",
                    "fullName": "Ada Lovelace",
                },
                description=(
                    "`09123456789` is normalized to `+989123456789`; "
                    "`fullName` is stored as `nickName`."
                ),
                request_only=True,
            ),
            OpenApiExample(
                "Iran national number response",
                value={
                    "accessToken": "<access JWT>",
                    "refreshToken": "<opaque refresh token>",
                    "user": {
                        "id": "8d9a1f2b-3c4d-4e5f-8a6b-7c8d9e0f1a2b",
                        "phone": "+989123456789",
                        "nickName": "Ada Lovelace",
                    },
                },
                description=(
                    "The stored and returned `phone` is `+989123456789`; "
                    "`fullName` is returned as `nickName`."
                ),
                response_only=True,
            ),
        ],
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
                full_name=serializer.validated_data.get("fullName", ""),
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
            "SMS. Verification uses the configured mock code "
            "(`AUTH_OTP_MOCK_CODE`, default `123456`). Public endpoint, "
            "throttled at 5 requests per minute per normalized phone number."
        ),
        auth=[],
        request=PhoneSerializer,
        examples=[
            OpenApiExample(
                "Iran national number",
                value={"countryCode": "IR", "phone": "09123456789"},
                description=(
                    "`09123456789` is normalized to `+989123456789`. No SMS is "
                    "sent by this stub."
                ),
                request_only=True,
            ),
        ],
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
        summary="Verify an OTP and issue tokens",
        description=(
            "Validates the required `code` against the configured mock code "
            "(`AUTH_OTP_MOCK_CODE`, default `123456`) and returns a real access "
            "token, rotating refresh token, and public user payload. The user "
            "is created if the phone number is not registered. Only code "
            "validation is mocked; the issued tokens use the normal token "
            "service. Public endpoint, throttled at 10 requests per minute per "
            "normalized phone number."
        ),
        auth=[],
        request=OtpVerifySerializer,
        examples=[
            OpenApiExample(
                "Iran national number",
                value={
                    "countryCode": "IR",
                    "phone": "09123456789",
                    "code": "123456",
                },
                description=(
                    "`09123456789` is normalized to `+989123456789`; `123456` "
                    "is the default mock verification code."
                ),
                request_only=True,
            ),
            OpenApiExample(
                "Iran national number response",
                value={
                    "accessToken": "<access JWT>",
                    "refreshToken": "<opaque refresh token>",
                    "user": {
                        "id": "8d9a1f2b-3c4d-4e5f-8a6b-7c8d9e0f1a2b",
                        "phone": "+989123456789",
                    },
                },
                description=(
                    "A real token pair and the user are returned; the `phone` "
                    "is the normalized E.164 value `+989123456789`."
                ),
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=TokenPairWithUserResponseSerializer,
                description=(
                    "OTP verified; real access and refresh tokens and the user "
                    "payload were returned."
                ),
            ),
            400: error_response(
                "Invalid or missing phone fields or missing `code` "
                "(`validation_error`)."
            ),
            401: error_response(
                "The verification code is not the configured mock code "
                "(`invalid_otp`)."
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

        try:
            user, pair = verify_otp(
                serializer.validated_data["phone_e164"],
                serializer.validated_data["code"],
            )
        except InvalidOtpCode as exc:
            raise ApiError(
                "Invalid or expired verification code.",
                code="invalid_otp",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        return _token_response(user, pair)
