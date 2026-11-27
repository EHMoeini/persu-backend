from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User

from .models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """Public facility shape returned by search."""

    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        coerce_to_string=False,
    )
    rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        coerce_to_string=False,
    )

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
            "description",
            "category",
            "type",
            "location",
            "price",
            "picture",
            "rating",
            "availability",
        )


class FacilityDetailSerializer(serializers.ModelSerializer):
    """Full facility details including coordinates, pricing, hours, sports, and amenities."""

    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        coerce_to_string=False,
    )
    rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        coerce_to_string=False,
    )

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
            "description",
            "category",
            "type",
            "location",
            "price",
            "picture",
            "rating",
            "availability",
            "city",
            "province",
            "district",
            "address",
            "latitude",
            "longitude",
            "phone",
            "price_irr",
            "price_display",
            "rating_count",
            "opening_hours",
            "sports",
            "amenities",
            "gender",
            "image_url",
            "source_name",
            "source_url",
        )


class FacilityListResponseSerializer(serializers.Serializer):
    """Facility search envelope."""

    facilities = FacilitySerializer(many=True, read_only=True)


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
