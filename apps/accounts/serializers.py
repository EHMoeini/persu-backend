"""Request validation and response serialization for auth endpoints."""

from __future__ import annotations

from rest_framework import serializers

from .models import User
from .phone import InvalidPhoneNumber, normalize_phone


class UserSerializer(serializers.ModelSerializer):
    """Public user shape: id, phone, and optional nickname/avatar."""

    phone = serializers.CharField(source="phone_e164", read_only=True)
    nickName = serializers.CharField(source="nick_name", read_only=True)
    avatar = serializers.URLField(read_only=True)

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
    countryCode = serializers.CharField(max_length=8)
    phone = serializers.CharField(max_length=32)

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
    )

    def validate_password(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Password is required.")
        return value


class RegisterSerializer(LoginSerializer):
    pass


class RefreshTokenSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=512,
    )

    def validate_refreshToken(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Refresh token is required.")
        return value


class LogoutSerializer(RefreshTokenSerializer):
    pass


class OtpVerifySerializer(PhoneSerializer):
    code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=16,
    )
