import json

from django.test import SimpleTestCase

from apps.common.handlers import handler404, handler500


class JsonHandlerTests(SimpleTestCase):
    def test_404_uses_error_envelope(self):
        response = handler404(None)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content),
            {
                "error": {
                    "code": "not_found",
                    "message": "Resource not found.",
                }
            },
        )

    def test_500_uses_error_envelope(self):
        response = handler500(None)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            json.loads(response.content),
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
        )
