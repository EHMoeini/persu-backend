from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields the authenticated user may update."""

    nickName = serializers.CharField(
        source="nick_name",
        required=False,
        allow_blank=True,
        max_length=64,
    )
    avatar = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=500,
    )

    class Meta:
        model = User
        fields = ("nickName", "avatar")
