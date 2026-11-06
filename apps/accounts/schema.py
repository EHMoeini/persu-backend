"""OpenAPI authentication scheme and response schemas for auth endpoints."""

from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import serializers


class PublicUserResponseSerializer(serializers.Serializer):
    """Public user shape returned by auth and profile endpoints."""

    id = serializers.UUIDField(help_text="User identifier.")
    phone = serializers.CharField(
        help_text="Phone number in E.164 format.",
    )
    nickName = serializers.CharField(
        required=False,
        max_length=64,
        help_text="Optional display name; omitted when empty.",
    )
    avatar = serializers.URLField(
        required=False,
        max_length=500,
        help_text="Optional avatar URL; omitted when empty.",
    )


class BearerAuthenticationScheme(OpenApiAuthenticationExtension):
    """Document the project's custom Bearer authentication for Swagger."""

    target_class = "apps.accounts.authentication.BearerAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Access JWT issued by POST /auth/login or POST /auth/register. "
                "Enter the accessToken value only; refresh tokens are rejected. "
                "Access tokens are short-lived (15 minutes by default)."
            ),
        }


class TokenPairResponseSerializer(serializers.Serializer):
    """Rotated access and refresh tokens."""

    accessToken = serializers.CharField(
        read_only=True,
        help_text="Short-lived access JWT.",
    )
    refreshToken = serializers.CharField(
        read_only=True,
        help_text=(
            "Opaque refresh token; store it securely and send it only to "
            "refresh or logout."
        ),
    )


class TokenPairWithUserResponseSerializer(TokenPairResponseSerializer):
    """Login or registration response with the public user payload."""

    user = PublicUserResponseSerializer()


class UserResponseSerializer(serializers.Serializer):
    """Authenticated user envelope."""

    user = PublicUserResponseSerializer()


class CheckResponseSerializer(serializers.Serializer):
    """Phone registration lookup result."""

    exists = serializers.BooleanField(
        read_only=True,
        help_text=(
            "True when the normalized phone number belongs to an account."
        ),
    )


class SuccessResponseSerializer(serializers.Serializer):
    """OTP stub response."""

    success = serializers.BooleanField(read_only=True)
