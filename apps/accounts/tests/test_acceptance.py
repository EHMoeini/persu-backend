from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import RefreshToken, User


class AccountLifecycleAcceptanceTests(APITestCase):
    password = "correct horse battery staple"
    country = "GB"
    phone = "020 7183 8750"
    e164 = "+442071838750"

    def setUp(self):
        cache.clear()

    def create_user(self):
        return User.objects.create_user(
            phone_e164=self.e164,
            password=self.password,
        )

    def register(self):
        return self.client.post(
            "/auth/register",
            {
                "countryCode": self.country,
                "phone": self.phone,
                "password": self.password,
            },
            format="json",
        )

    def login(self):
        return self.client.post(
            "/auth/login",
            {
                "countryCode": self.country,
                "phone": self.phone,
                "password": self.password,
            },
            format="json",
        )

    def refresh(self, token: str):
        return self.client.post(
            "/auth/refresh",
            {"refreshToken": token},
            format="json",
        )

    def logout(self, token: str):
        return self.client.post(
            "/auth/logout",
            {"refreshToken": token},
            format="json",
        )

    def me(self, token: str | None = None):
        headers = {}
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.get("/api/me", **headers)

    def assert_error(self, response, status_code: int, code: str):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.json()["error"]["code"], code)

    def test_register_login_refresh_logout_lifecycle(self):
        registered = self.register()
        self.assertEqual(registered.status_code, 201)
        registered_data = registered.json()
        self.assertEqual(registered_data["user"]["phone"], self.e164)

        check = self.client.post(
            "/auth/check",
            {"countryCode": self.country, "phone": self.phone},
            format="json",
        )
        self.assertEqual(check.json(), {"exists": True})

        logged_in = self.login()
        self.assertEqual(logged_in.status_code, 200)
        login_data = logged_in.json()

        # Login starts a new family and revokes the registration family.
        self.assert_error(
            self.refresh(registered_data["refreshToken"]),
            401,
            "invalid_refresh_token",
        )
        self.assertEqual(self.me(login_data["accessToken"]).status_code, 200)

        rotated = self.refresh(login_data["refreshToken"])
        self.assertEqual(rotated.status_code, 200)
        rotated_data = rotated.json()
        self.assertEqual(self.me(rotated_data["accessToken"]).status_code, 200)

        self.assertEqual(
            self.logout(rotated_data["refreshToken"]).status_code,
            204,
        )
        self.assert_error(
            self.refresh(rotated_data["refreshToken"]),
            401,
            "invalid_refresh_token",
        )

    def test_refresh_reuse_revokes_the_family(self):
        self.create_user()
        tokens = self.login().json()
        rotated = self.refresh(tokens["refreshToken"]).json()

        self.assert_error(
            self.refresh(tokens["refreshToken"]),
            401,
            "invalid_refresh_token",
        )
        self.assert_error(
            self.refresh(rotated["refreshToken"]),
            401,
            "invalid_refresh_token",
        )
        self.assertEqual(
            RefreshToken.objects.filter(revoked_at__isnull=True).count(),
            0,
        )

    def test_second_login_invalidates_old_refresh_but_not_old_access(self):
        self.create_user()
        first = self.login().json()
        second = self.login().json()

        self.assert_error(
            self.refresh(first["refreshToken"]),
            401,
            "invalid_refresh_token",
        )
        self.assertEqual(self.refresh(second["refreshToken"]).status_code, 200)

        # Access tokens stay valid until expiry by design.
        self.assertEqual(self.me(first["accessToken"]).status_code, 200)

    def test_refresh_token_cannot_authenticate_resource_requests(self):
        self.create_user()
        tokens = self.login().json()

        self.assert_error(
            self.me(tokens["refreshToken"]),
            401,
            "unauthorized",
        )

    def test_duplicate_registration_does_not_break_later_requests(self):
        self.assertEqual(self.register().status_code, 201)

        self.assert_error(
            self.register(),
            409,
            "phone_already_registered",
        )

        check = self.client.post(
            "/auth/check",
            {"countryCode": self.country, "phone": self.phone},
            format="json",
        )
        self.assertEqual(check.status_code, 200)
        self.assertEqual(check.json(), {"exists": True})
        self.assertEqual(self.login().status_code, 200)

    def test_errors_use_the_standard_envelope(self):
        responses = [
            (self.me(), 401, "unauthorized"),
            (
                self.client.post("/auth/check", {}, format="json"),
                400,
                "validation_error",
            ),
            (
                self.client.get("/api/missing"),
                404,
                "not_found",
            ),
            (
                self.client.get("/auth/check"),
                405,
                "method_not_allowed",
            ),
            (
                self.client.generic(
                    "POST",
                    "/auth/check",
                    data="{not-json",
                    content_type="application/json",
                ),
                400,
                "invalid_json",
            ),
        ]

        for response, status_code, code in responses:
            with self.subTest(code=code):
                self.assert_error(response, status_code, code)
                self.assertEqual(set(response.json()), {"error"})
                self.assertEqual(
                    set(response.json()["error"]),
                    {"code", "message"},
                )
