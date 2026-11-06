from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .schema import HealthResponseSerializer, error_response


class HealthView(APIView):
    """Unauthenticated liveness endpoint."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        tags=["Health"],
        summary="Service liveness check",
        description=(
            "Unauthenticated liveness endpoint used by deployment health "
            "checks. It is exempt from the HTTPS redirect for internal checks."
        ),
        auth=[],
        responses={
            200: OpenApiResponse(
                response=HealthResponseSerializer,
                description="Service is running.",
            ),
            500: error_response("Unhandled server error (`internal_error`)."),
        },
    )
    def get(self, request) -> Response:
        return Response({"status": "ok"})
