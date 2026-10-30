from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tokens import issue_access_token


@override_settings(ROOT_URLCONF="apps.accounts.tests.urls")
class BearerAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="correct horse battery staple",
        )

    def test_valid_access_token_authenticates_request(self):
        token = issue_access_token(self.user)

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], str(self.user.id))
        self.assertEqual(response.json()["typ"], "access")
        self.assertTrue(response.json()["jti"])

    def test_missing_authorization_returns_401_with_challenge(self):
        response = self.client.get("/protected")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")
        self.assertIn("Bearer", response["WWW-Authenticate"])

    def test_invalid_access_token_returns_401(self):
        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION="Bearer not-a-jwt",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")

    def test_expired_access_token_returns_401(self):
        token = issue_access_token(self.user, ttl_seconds=-1)

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")

    def test_inactive_user_returns_401(self):
        token = issue_access_token(self.user)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_deleted_user_returns_401(self):
        token = issue_access_token(self.user)
        self.user.delete()

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_wrong_scheme_returns_401(self):
        token = issue_access_token(self.user)

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Basic {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_malformed_bearer_header_returns_401(self):
        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION="Bearer",
        )

        self.assertEqual(response.status_code, 401)

    def test_client_supplied_user_id_is_ignored(self):
        other = User.objects.create_user(
            phone_e164="+442071838750",
            password="another password",
        )
        token = issue_access_token(self.user)

        response = self.client.get(
            "/protected",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_USER_ID=str(other.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], str(self.user.id))
