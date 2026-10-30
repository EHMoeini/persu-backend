from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed, Throttled, ValidationError

from apps.common.exceptions import ApiError, api_exception_handler


class ErrorEnvelopeTests(TestCase):
    def test_custom_api_error_preserves_code_and_status(self):
        exc = ApiError(
            "Phone already registered.",
            code="phone_already_registered",
            status_code=409,
        )

        response = api_exception_handler(exc, {})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "phone_already_registered",
                    "message": "Phone already registered.",
                }
            },
        )

    def test_validation_errors_are_generic(self):
        response = api_exception_handler(
            ValidationError({"phone": ["This field is required."]}), {}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request data.",
                }
            },
        )

    def test_authentication_errors_use_unauthorized_code(self):
        response = api_exception_handler(AuthenticationFailed("Bad token."), {})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "unauthorized")

    def test_throttle_errors_use_rate_limited_code(self):
        response = api_exception_handler(Throttled(wait=30), {})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["error"]["code"], "rate_limited")

    def test_unhandled_errors_are_logged_and_hidden(self):
        with self.assertLogs("apps.common.exceptions", level="ERROR"):
            response = api_exception_handler(RuntimeError("database exploded"), {})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
        )
