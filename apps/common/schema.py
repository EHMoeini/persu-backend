"""OpenAPI response schemas and helpers shared by API views."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    """Stable error code with a client-safe message."""

    code = serializers.CharField(
        read_only=True,
        help_text="Machine-readable error code.",
    )
    message = serializers.CharField(
        read_only=True,
        help_text="Human-readable error message.",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Uniform error envelope produced by the API exception handler."""

    error = ErrorDetailSerializer(read_only=True)


class HealthResponseSerializer(serializers.Serializer):
    """Liveness response."""

    status = serializers.CharField(
        read_only=True,
        help_text='Always "ok" when the service is healthy.',
    )


def error_response(description: str) -> OpenApiResponse:
    """Build an error response entry using the shared error envelope."""

    return OpenApiResponse(
        response=ErrorResponseSerializer,
        description=description,
    )
