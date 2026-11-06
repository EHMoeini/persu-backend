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
        help_text="Optional display name; an empty string clears it.",
    )
    avatar = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional avatar URL; an empty string clears it.",
    )

    class Meta:
        model = User
        fields = ("nickName", "avatar")
