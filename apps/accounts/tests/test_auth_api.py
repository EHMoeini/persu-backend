from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import RefreshToken, User
from apps.accounts.tokens import decode_access_token, issue_access_token, issue_token_pair


class AuthApiTestCase(APITestCase):
    password = "correct horse battery staple"
    phone = "+12024561111"
    country = "US"
    national = "2024561111"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            phone_e164=self.phone,
            password=self.password,
        )

    def login(
        self,
        *,
        country: str = "US",
        phone: str = "2024561111",
        password: str | None = None,
    ):
        return self.client.post(
            "/auth/login",
            {
                "countryCode": country,
                "phone": phone,
                "password": self.password if password is None else password,
            },
            format="json",
        )

    def register(
        self,
        *,
        country: str = "GB",
        phone: str = "020 7183 8750",
        password: str | None = None,
    ):
        return self.client.post(
            "/auth/register",
            {
                "countryCode": country,
                "phone": phone,
                "password": self.password if password is None else password,
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

    def session(self, token: str | None = None):
        headers = {}
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.get("/auth/session", **headers)

    def assert_error(self, response, status_code: int, code: str):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.json()["error"]["code"], code)


class CheckApiTests(AuthApiTestCase):
    def test_existing_phone_returns_true(self):
        response = self.client.post(
            "/auth/check",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"exists": True})

    def test_unknown_phone_returns_false(self):
        response = self.client.post(
            "/auth/check",
            {"countryCode": "GB", "phone": "020 7183 8750"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"exists": False})

    def test_phone_is_normalized_before_lookup(self):
        response = self.client.post(
            "/auth/check",
            {"countryCode": "+1", "phone": "(202) 456-1111"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"exists": True})

    def test_invalid_phone_returns_validation_error(self):
        response = self.client.post(
            "/auth/check",
            {"countryCode": "US", "phone": "12345"},
            format="json",
        )

        self.assert_error(response, 400, "validation_error")

    def test_missing_fields_returns_validation_error(self):
        response = self.client.post("/auth/check", {}, format="json")

        self.assert_error(response, 400, "validation_error")

    def test_check_is_rate_limited_per_phone(self):
        payload = {"countryCode": "US", "phone": "2024561111"}

        for _ in range(10):
            response = self.client.post("/auth/check", payload, format="json")
            self.assertEqual(response.status_code, 200)

        response = self.client.post("/auth/check", payload, format="json")
        self.assert_error(response, 429, "rate_limited")

    def test_rate_limit_does_not_affect_another_phone(self):
        payload = {"countryCode": "US", "phone": "2024561111"}
        for _ in range(10):
            self.client.post("/auth/check", payload, format="json")

        response = self.client.post(
            "/auth/check",
            {"countryCode": "GB", "phone": "020 7183 8750"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_phone_attempts_share_ip_rate_limit(self):
        for index in range(10):
            response = self.client.post(
                "/auth/check",
                {"countryCode": "US", "phone": f"1234{index}"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/auth/check",
            {"countryCode": "US", "phone": "999999"},
            format="json",
        )

        self.assert_error(response, 429, "rate_limited")

    def test_auth_routes_emit_cors_headers(self):
        origin = settings.CORS_ALLOWED_ORIGINS[0]
        response = self.client.post(
            "/auth/check",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
            HTTP_ORIGIN=origin,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], origin)

    def test_iran_national_number_is_normalized(self):
        User.objects.create_user(
            phone_e164="+989123456789",
            password=self.password,
        )

        response = self.client.post(
            "/auth/check",
            {"countryCode": "IR", "phone": "09123456789"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"exists": True})


class LoginApiTests(AuthApiTestCase):
    def test_login_returns_tokens_and_user(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"accessToken", "refreshToken", "user"})
        self.assertEqual(data["user"]["id"], str(self.user.id))
        self.assertEqual(data["user"]["phone"], self.phone)
        self.assertNotIn("password", data["user"])
        self.assertNotIn("phone_e164", data["user"])

        claims = decode_access_token(data["accessToken"])
        self.assertEqual(claims.user_id, self.user.id)
        self.assertEqual(
            RefreshToken.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

    def test_login_accepts_dialing_code_and_punctuation(self):
        response = self.login(country="+1", phone="(202) 456-1111")

        self.assertEqual(response.status_code, 200)

    def test_invalid_password_returns_generic_401(self):
        response = self.login(password="wrong password")

        self.assert_error(response, 401, "invalid_credentials")
        self.assertEqual(
            response.json()["error"]["message"],
            "Invalid phone number or password.",
        )

    def test_unknown_phone_returns_same_generic_401(self):
        response = self.login(country="GB", phone="020 7183 8750")

        self.assert_error(response, 401, "invalid_credentials")
        self.assertEqual(
            response.json()["error"]["message"],
            "Invalid phone number or password.",
        )

    def test_inactive_user_returns_generic_401(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.login()

        self.assert_error(response, 401, "invalid_credentials")

    def test_missing_password_returns_validation_error(self):
        response = self.client.post(
            "/auth/login",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
        )

        self.assert_error(response, 400, "validation_error")

    def test_second_login_invalidates_first_refresh_token(self):
        first = self.login().json()
        second = self.login().json()

        response = self.refresh(first["refreshToken"])
        self.assert_error(response, 401, "invalid_refresh_token")

        # Second family remains valid.
        response = self.refresh(second["refreshToken"])
        self.assertEqual(response.status_code, 200)

    def test_login_is_rate_limited_per_phone(self):
        for _ in range(5):
            response = self.login(password="wrong password")
            self.assertEqual(response.status_code, 401)

        response = self.login(password="wrong password")
        self.assert_error(response, 429, "rate_limited")

    def test_login_rate_limit_does_not_affect_another_phone(self):
        for _ in range(5):
            self.login(password="wrong password")

        response = self.client.post(
            "/auth/login",
            {
                "countryCode": "GB",
                "phone": "020 7183 8750",
                "password": "wrong password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)


class RegisterApiTests(AuthApiTestCase):
    def test_register_creates_user_and_returns_tokens(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(set(data), {"accessToken", "refreshToken", "user"})
        self.assertEqual(data["user"]["phone"], "+442071838750")

        user = User.objects.get(phone_e164="+442071838750")
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(
            RefreshToken.objects.filter(
                user=user,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

    def test_register_accepts_full_name(self):
        response = self.client.post(
            "/auth/register",
            {
                "countryCode": "IR",
                "phone": "09123456789",
                "password": self.password,
                "fullName": "Ada Lovelace",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["phone"], "+989123456789")
        self.assertEqual(response.json()["user"]["nickName"], "Ada Lovelace")

        user = User.objects.get(phone_e164="+989123456789")
        self.assertEqual(user.nick_name, "Ada Lovelace")

    def test_register_without_full_name_omits_nick_name(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("nickName", response.json()["user"])

    def test_register_duplicate_returns_409(self):
        response = self.register(country="US", phone="2024561111")

        self.assert_error(response, 409, "phone_already_registered")

    def test_register_duplicate_across_normalized_formats_returns_409(self):
        response = self.register(country="1", phone="(202) 456-1111")

        self.assert_error(response, 409, "phone_already_registered")

    def test_register_invalid_phone_returns_validation_error(self):
        response = self.register(country="US", phone="12345")

        self.assert_error(response, 400, "validation_error")

    def test_register_missing_password_returns_validation_error(self):
        response = self.client.post(
            "/auth/register",
            {"countryCode": "GB", "phone": "020 7183 8750"},
            format="json",
        )

        self.assert_error(response, 400, "validation_error")

    def test_register_is_rate_limited_per_phone(self):
        for _ in range(5):
            response = self.register(country="US", phone="2024561111")
            self.assertEqual(response.status_code, 409)

        response = self.register(country="US", phone="2024561111")
        self.assert_error(response, 429, "rate_limited")


class RefreshApiTests(AuthApiTestCase):
    def test_refresh_rotates_tokens(self):
        tokens = self.login().json()

        response = self.refresh(tokens["refreshToken"])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"accessToken", "refreshToken"})
        self.assertNotEqual(data["refreshToken"], tokens["refreshToken"])
        self.assertEqual(
            decode_access_token(data["accessToken"]).user_id,
            self.user.id,
        )

    def test_old_refresh_token_fails_after_rotation(self):
        tokens = self.login().json()
        self.refresh(tokens["refreshToken"])

        response = self.refresh(tokens["refreshToken"])

        self.assert_error(response, 401, "invalid_refresh_token")

    def test_reuse_revokes_the_whole_family(self):
        tokens = self.login().json()
        rotated = self.refresh(tokens["refreshToken"]).json()

        response = self.refresh(tokens["refreshToken"])
        self.assert_error(response, 401, "invalid_refresh_token")

        response = self.refresh(rotated["refreshToken"])
        self.assert_error(response, 401, "invalid_refresh_token")
        self.assertEqual(
            RefreshToken.objects.filter(revoked_at__isnull=True).count(),
            0,
        )

    def test_invalid_refresh_token_returns_401(self):
        response = self.refresh("unknown-token")

        self.assert_error(response, 401, "invalid_refresh_token")

    def test_expired_refresh_token_returns_401(self):
        pair = issue_token_pair(self.user, refresh_ttl_seconds=-1)

        response = self.refresh(pair.refresh_token)

        self.assert_error(response, 401, "invalid_refresh_token")

    def test_missing_refresh_token_returns_validation_error(self):
        response = self.client.post("/auth/refresh", {}, format="json")

        self.assert_error(response, 400, "validation_error")

    def test_refresh_is_rate_limited_per_token(self):
        for _ in range(20):
            response = self.refresh("unknown-token")
            self.assertEqual(response.status_code, 401)

        response = self.refresh("unknown-token")
        self.assert_error(response, 429, "rate_limited")


class LogoutApiTests(AuthApiTestCase):
    def test_logout_revokes_family(self):
        tokens = self.login().json()

        response = self.logout(tokens["refreshToken"])

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        response = self.refresh(tokens["refreshToken"])
        self.assert_error(response, 401, "invalid_refresh_token")

    def test_logout_is_idempotent(self):
        tokens = self.login().json()

        self.assertEqual(
            self.logout(tokens["refreshToken"]).status_code,
            204,
        )
        self.assertEqual(
            self.logout(tokens["refreshToken"]).status_code,
            204,
        )
        self.assertEqual(self.logout("unknown-token").status_code, 204)

    def test_logout_missing_token_returns_validation_error(self):
        response = self.client.post("/auth/logout", {}, format="json")

        self.assert_error(response, 400, "validation_error")


class SessionApiTests(AuthApiTestCase):
    def test_session_returns_user_from_access_token(self):
        token = issue_access_token(self.user)

        response = self.session(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], str(self.user.id))
        self.assertEqual(response.json()["user"]["phone"], self.phone)
        self.assertNotIn("password", response.json()["user"])

    def test_session_requires_access_token(self):
        response = self.session()

        self.assert_error(response, 401, "unauthorized")

    def test_session_rejects_invalid_access_token(self):
        response = self.session("not-a-jwt")

        self.assert_error(response, 401, "unauthorized")

    def test_session_rejects_expired_access_token(self):
        token = issue_access_token(self.user, ttl_seconds=-1)

        response = self.session(token)

        self.assert_error(response, 401, "unauthorized")

    def test_session_rejects_refresh_token_as_bearer(self):
        tokens = self.login().json()

        response = self.session(tokens["refreshToken"])

        self.assert_error(response, 401, "unauthorized")

    def test_session_returns_optional_profile_fields(self):
        self.user.nick_name = "Ada"
        self.user.avatar = "https://example.com/avatar.png"
        self.user.save(update_fields=["nick_name", "avatar"])
        token = issue_access_token(self.user)

        response = self.session(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["nickName"], "Ada")
        self.assertEqual(
            response.json()["user"]["avatar"],
            "https://example.com/avatar.png",
        )


class UserPayloadTests(AuthApiTestCase):
    def test_optional_fields_are_omitted_when_empty(self):
        user = self.login().json()["user"]

        self.assertEqual(set(user), {"id", "phone"})
        self.assertEqual(user["phone"], self.phone)

    def test_internal_fields_are_never_exposed(self):
        user = self.login().json()["user"]

        self.assertNotIn("password", user)
        self.assertNotIn("password_hash", user)
        self.assertNotIn("phone_e164", user)
        self.assertNotIn("is_staff", user)


class OtpApiTests(AuthApiTestCase):
    def test_otp_send_always_succeeds(self):
        response = self.client.post(
            "/auth/otp/send",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

    def verify(self, *, country="US", phone="2024561111", code="123456"):
        return self.client.post(
            "/auth/otp/verify",
            {"countryCode": country, "phone": phone, "code": code},
            format="json",
        )

    def test_otp_verify_returns_real_tokens_and_user(self):
        response = self.verify()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"accessToken", "refreshToken", "user"})
        self.assertEqual(data["user"]["id"], str(self.user.id))
        self.assertEqual(data["user"]["phone"], self.phone)

        claims = decode_access_token(data["accessToken"])
        self.assertEqual(claims.user_id, self.user.id)
        self.assertEqual(
            RefreshToken.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

        session = self.session(data["accessToken"])
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["user"]["id"], str(self.user.id))

    def test_otp_verify_creates_user_for_unknown_phone(self):
        response = self.verify(country="IR", phone="09123456789")

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(phone_e164="+989123456789")
        self.assertEqual(response.json()["user"]["id"], str(user.id))
        self.assertEqual(response.json()["user"]["phone"], "+989123456789")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            RefreshToken.objects.filter(
                user=user,
                revoked_at__isnull=True,
            ).exists()
        )

    def test_otp_verify_rejects_wrong_code(self):
        response = self.verify(code="000000")

        self.assert_error(response, 401, "invalid_otp")
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(RefreshToken.objects.filter(user=self.user).exists())

    def test_otp_verify_requires_code(self):
        response = self.client.post(
            "/auth/otp/verify",
            {"countryCode": "US", "phone": "2024561111"},
            format="json",
        )

        self.assert_error(response, 400, "validation_error")

    def test_otp_verify_is_rate_limited(self):
        for _ in range(10):
            response = self.verify(code="000000")
            self.assertEqual(response.status_code, 401)

        response = self.verify(code="000000")
        self.assert_error(response, 429, "rate_limited")

    def test_otp_invalid_phone_returns_validation_error(self):
        response = self.client.post(
            "/auth/otp/send",
            {"countryCode": "US", "phone": "12345"},
            format="json",
        )

        self.assert_error(response, 400, "validation_error")

    def test_otp_send_is_rate_limited(self):
        payload = {"countryCode": "US", "phone": "2024561111"}
        for _ in range(5):
            response = self.client.post("/auth/otp/send", payload, format="json")
            self.assertEqual(response.status_code, 200)

        response = self.client.post("/auth/otp/send", payload, format="json")
        self.assert_error(response, 429, "rate_limited")
