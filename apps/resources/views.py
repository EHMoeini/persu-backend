from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import BearerAuthentication
from apps.accounts.permissions import IsAuthenticatedUser
from apps.accounts.serializers import UserSerializer

from .serializers import ProfileUpdateSerializer


class MeView(APIView):
    """Authenticated profile endpoints."""

    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedUser]

    def get(self, request) -> Response:
        return Response({"user": UserSerializer(request.user).data})

    def patch(self, request) -> Response:
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": UserSerializer(user).data})
