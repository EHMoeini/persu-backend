from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tokens import issue_access_token, issue_token_pair


class MeResourceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="correct horse battery staple",
        )
        self.token = issue_access_token(self.user)

    def auth_get(self, token: str | None = None):
        headers = {}
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.get("/api/me", **headers)

    def auth_patch(self, data: dict, token: str | None = None, **extra):
        headers = dict(extra)
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.patch("/api/me", data, format="json", **headers)

    def test_get_me_returns_authenticated_user(self):
        response = self.auth_get(self.token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], str(self.user.id))
        self.assertEqual(response.json()["user"]["phone"], "+12024561111")
        self.assertNotIn("password", response.json()["user"])
        self.assertNotIn("phone_e164", response.json()["user"])

    def test_get_me_requires_access_token(self):
        response = self.auth_get()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")

    def test_get_me_rejects_invalid_access_token(self):
        response = self.auth_get("not-a-jwt")

        self.assertEqual(response.status_code, 401)

    def test_get_me_rejects_expired_access_token(self):
        expired = issue_access_token(self.user, ttl_seconds=-1)

        response = self.auth_get(expired)

        self.assertEqual(response.status_code, 401)

    def test_get_me_rejects_refresh_token_as_bearer(self):
        pair = issue_token_pair(self.user)

        response = self.auth_get(pair.refresh_token)

        self.assertEqual(response.status_code, 401)

    def test_get_me_works_for_server_to_server_call_without_origin(self):
        response = self.auth_get(self.token)

        self.assertEqual(response.status_code, 200)

    def test_patch_updates_profile(self):
        response = self.auth_patch(
            {
                "nickName": "Ada",
                "avatar": "https://example.com/avatar.png",
            },
            self.token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["nickName"], "Ada")
        self.assertEqual(
            response.json()["user"]["avatar"],
            "https://example.com/avatar.png",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.nick_name, "Ada")
        self.assertEqual(self.user.avatar, "https://example.com/avatar.png")

    def test_patch_can_clear_optional_fields(self):
        self.user.nick_name = "Ada"
        self.user.avatar = "https://example.com/avatar.png"
        self.user.save(update_fields=["nick_name", "avatar"])

        response = self.auth_patch(
            {"nickName": "", "avatar": ""},
            self.token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("nickName", response.json()["user"])
        self.assertNotIn("avatar", response.json()["user"])

    def test_patch_does_not_change_phone_or_id(self):
        original_id = self.user.id
        original_phone = self.user.phone_e164

        response = self.auth_patch(
            {
                "nickName": "Ada",
                "phone": "+442071838750",
                "phone_e164": "+442071838750",
                "id": "00000000-0000-0000-0000-000000000000",
            },
            self.token,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.id, original_id)
        self.assertEqual(self.user.phone_e164, original_phone)

    def test_patch_ignores_client_supplied_user_id_header(self):
        other = User.objects.create_user(
            phone_e164="+442071838750",
            password="another password",
        )

        response = self.auth_patch(
            {"nickName": "Ada"},
            self.token,
            HTTP_X_USER_ID=str(other.id),
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.nick_name, "Ada")
        self.assertEqual(other.nick_name, "")

    def test_patch_requires_access_token(self):
        response = self.auth_patch({"nickName": "Ada"})

        self.assertEqual(response.status_code, 401)

    def test_patch_rejects_invalid_avatar(self):
        response = self.auth_patch(
            {"avatar": "not-a-url"},
            self.token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")
