"""Request validation and response serialization for auth endpoints."""

from __future__ import annotations

from rest_framework import serializers

from .models import User
from .phone import InvalidPhoneNumber, normalize_phone


class UserSerializer(serializers.ModelSerializer):
    """Public user shape: id, phone, and optional nickname/avatar."""

    phone = serializers.CharField(
        source="phone_e164",
        read_only=True,
        help_text="Phone number in E.164 format.",
    )
    nickName = serializers.CharField(
        source="nick_name",
        read_only=True,
        help_text="Optional display name; omitted when empty.",
    )
    avatar = serializers.URLField(
        read_only=True,
        help_text="Optional avatar URL; omitted when empty.",
    )

    class Meta:
        model = User
        fields = ("id", "phone", "nickName", "avatar")

    def to_representation(self, instance: User) -> dict:
        data = super().to_representation(instance)
        if not data.get("nickName"):
            data.pop("nickName", None)
        if not data.get("avatar"):
            data.pop("avatar", None)
        return data


class PhoneSerializer(serializers.Serializer):
    countryCode = serializers.CharField(
        max_length=8,
        help_text=(
            "ISO country code (for example US or IR) or dialing code "
            "(for example +1 or +98)."
        ),
    )
    phone = serializers.CharField(
        max_length=32,
        help_text=(
            "National phone number; normalized to E.164 before use. For "
            "example, `IR` + `09123456789` becomes `+989123456789`."
        ),
    )

    def validate(self, attrs: dict) -> dict:
        try:
            attrs["phone_e164"] = normalize_phone(
                attrs["countryCode"],
                attrs["phone"],
            )
        except InvalidPhoneNumber as exc:
            raise serializers.ValidationError({"phone": str(exc)}) from exc
        return attrs


class LoginSerializer(PhoneSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
        help_text="Account password; whitespace-only values are rejected.",
    )

    def validate_password(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Password is required.")
        return value


class RegisterSerializer(LoginSerializer):
    fullName = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=64,
        write_only=True,
        help_text=(
            "Optional full name. Stored as the profile nickname and returned "
            "as `nickName`."
        ),
    )


class RefreshTokenSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=512,
        help_text=(
            "Opaque refresh token from login, registration, or the previous "
            "refresh response."
        ),
    )

    def validate_refreshToken(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Refresh token is required.")
        return value


class LogoutSerializer(RefreshTokenSerializer):
    pass


class OtpVerifySerializer(PhoneSerializer):
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=16,
        help_text=(
            "Verification code. The code is validated against the configured "
            "mock code (`AUTH_OTP_MOCK_CODE`, default `123456`); the returned "
            "tokens are real."
        ),
    )
