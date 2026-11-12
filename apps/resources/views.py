from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import BearerAuthentication
from apps.accounts.permissions import IsAuthenticatedUser
from apps.accounts.schema import UserResponseSerializer
from apps.accounts.serializers import UserSerializer
from apps.common.schema import error_response

from .models import Facility
from .search import search_facilities
from .serializers import (
    FacilityListResponseSerializer,
    FacilitySerializer,
    ProfileUpdateSerializer,
)


class FacilityListView(APIView):
    """Public facility search endpoint."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Facilities"],
        summary="Search facilities",
        description=(
            "Searches facility name, type, and location in Persian or English. "
            "Matches are partial, case-insensitive, and tolerant of Persian/"
            "Arabic character variants (`ي`/`ی`, `ك`/`ک`), extra spaces, and "
            "ZWNJ, and small spelling variations. Related terms are recognized, "
            "so `شنا` finds pools and `فوتبال` finds artificial turf. Results are "
            "ordered by relevance. "
            "A missing or blank `q` returns every facility. No authentication "
            "is required."
        ),
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Partial, case-insensitive search text.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=FacilityListResponseSerializer,
                description="Matching facilities.",
            ),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def get(self, request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        facilities = search_facilities(Facility.objects.all(), query)
        return Response(
            {"facilities": FacilitySerializer(facilities, many=True).data}
        )


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
