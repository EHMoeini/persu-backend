from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import BearerAuthentication
from apps.accounts.permissions import IsAuthenticatedUser
from apps.accounts.schema import UserResponseSerializer
from apps.accounts.serializers import UserSerializer
from apps.common.schema import error_response

from .serializers import ProfileUpdateSerializer


class MeView(APIView):
    """Authenticated profile endpoints."""

    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        tags=["Profile"],
        summary="Get the authenticated user's profile",
        description=(
            "Returns the public user payload identified by the Bearer access "
            "token. Requires an active authenticated user. Optional `nickName` "
            "and `avatar` fields are omitted when empty."
        ),
        responses={
            200: OpenApiResponse(
                response=UserResponseSerializer,
                description="Authenticated user's profile.",
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

    @extend_schema(
        tags=["Profile"],
        summary="Update the authenticated user's profile",
        description=(
            "Partially updates `nickName` and/or `avatar` and returns the "
            "updated public user payload. Both fields are optional; an empty "
            "string clears a field, and `{}` is a valid no-op. Identity, phone, "
            "password, and unknown fields are ignored."
        ),
        request=ProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserResponseSerializer,
                description="Updated authenticated user's profile.",
            ),
            400: error_response(
                "Invalid profile fields, such as a malformed avatar URL "
                "(`validation_error`)."
            ),
            401: error_response(
                "Missing, invalid, expired, or inactive-user access token "
                "(`unauthorized`)."
            ),
            415: error_response(
                "Unsupported request media type (`unsupported_media_type`)."
            ),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def patch(self, request) -> Response:
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": UserSerializer(user).data})
