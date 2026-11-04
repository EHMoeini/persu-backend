from django.conf import settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tokens import issue_access_token

ALLOWED_ORIGIN = settings.CORS_ALLOWED_ORIGINS[0]
DISALLOWED_ORIGIN = "https://evil.example.com"


class ResourceCorsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="correct horse battery staple",
        )
        self.token = issue_access_token(self.user)
        self.auth_header = f"Bearer {self.token}"

    def preflight(self, path: str = "/api/me", method: str = "GET"):
        return self.client.options(
            path,
            HTTP_ORIGIN=ALLOWED_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )

    def test_preflight_allows_configured_origin_headers_and_methods(self):
        response = self.preflight()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )

        allowed_headers = response["Access-Control-Allow-Headers"].lower()
        self.assertIn("authorization", allowed_headers)
        self.assertIn("content-type", allowed_headers)

        allowed_methods = response["Access-Control-Allow-Methods"].upper()
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            self.assertIn(method, allowed_methods)

        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_preflight_for_patch_is_allowed(self):
        response = self.preflight(method="PATCH")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "PATCH",
            response["Access-Control-Allow-Methods"].upper(),
        )

    def test_preflight_does_not_require_an_access_token(self):
        response = self.preflight()

        self.assertEqual(response.status_code, 200)

    def test_authenticated_get_returns_cors_headers(self):
        response = self.client.get(
            "/api/me",
            HTTP_AUTHORIZATION=self.auth_header,
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_patch_returns_cors_headers(self):
        response = self.client.patch(
            "/api/me",
            {"nickName": "Ada"},
            format="json",
            HTTP_AUTHORIZATION=self.auth_header,
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )

    def test_unauthorized_response_still_has_cors_headers(self):
        response = self.client.get(
            "/api/me",
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_validation_error_still_has_cors_headers(self):
        response = self.client.patch(
            "/api/me",
            {"avatar": "not-a-url"},
            format="json",
            HTTP_AUTHORIZATION=self.auth_header,
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )

    def test_disallowed_origin_gets_no_cors_header(self):
        response = self.client.get(
            "/api/me",
            HTTP_AUTHORIZATION=self.auth_header,
            HTTP_ORIGIN=DISALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_not_found_under_api_still_has_cors_headers(self):
        response = self.client.get(
            "/api/missing",
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            ALLOWED_ORIGIN,
        )

    def test_auth_routes_are_not_cors_enabled(self):
        preflight = self.preflight(path="/auth/check", method="POST")
        self.assertNotIn("Access-Control-Allow-Origin", preflight)

        response = self.client.post(
            "/auth/check",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
            HTTP_ORIGIN=ALLOWED_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)
