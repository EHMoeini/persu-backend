"""JSON handlers for errors raised outside DRF views."""

from __future__ import annotations

from django.http import JsonResponse


def handler404(request, exception=None) -> JsonResponse:
    return JsonResponse(
        {"error": {"code": "not_found", "message": "Resource not found."}},
        status=404,
    )


def handler500(request) -> JsonResponse:
    return JsonResponse(
        {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
            }
        },
        status=500,
    )
