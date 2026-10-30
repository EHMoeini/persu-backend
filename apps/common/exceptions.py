"""Consistent API error envelopes."""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    Throttled,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ApiError(APIException):
    """Client-safe API error."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Request could not be processed."
    default_code = "bad_request"

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.default_code = code
        super().__init__(detail=detail or self.default_detail, code=self.default_code)


def _error_payload(exc: Exception) -> tuple[str, str]:
    """Map an exception to a safe code and message."""
    if isinstance(exc, ApiError):
        return exc.default_code, str(exc.detail)

    if isinstance(exc, ValidationError):
        return "validation_error", "Invalid request data."

    if isinstance(exc, NotAuthenticated):
        return "unauthorized", "Authentication required."

    if isinstance(exc, AuthenticationFailed):
        return "unauthorized", "Authentication failed."

    if isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        return "forbidden", "You do not have permission to perform this action."

    if isinstance(exc, (NotFound, Http404)):
        return "not_found", "Resource not found."

    if isinstance(exc, Throttled):
        return "rate_limited", "Too many requests. Please try again later."

    if isinstance(exc, MethodNotAllowed):
        return "method_not_allowed", "Method not allowed."

    if isinstance(exc, ParseError):
        return "invalid_json", "Malformed JSON request."

    if isinstance(exc, UnsupportedMediaType):
        return "unsupported_media_type", "Unsupported media type."

    if isinstance(exc, APIException):
        return "bad_request", "Request could not be processed."

    return "internal_error", "An unexpected error occurred."


def api_exception_handler(exc: Exception, context: dict) -> Response:
    """Normalize DRF error responses."""
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API exception")
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code, message = _error_payload(exc)
    response.data = {"error": {"code": code, "message": message}}
    return response
