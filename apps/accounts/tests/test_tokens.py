from datetime import timedelta

import jwt
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tokens import (
    InvalidAccessToken,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    issue_access_token,
)


class AccessTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="correct horse battery staple",
        )

    def _decode_payload(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.AUTH_JWT["SECRET"],
            algorithms=[settings.AUTH_JWT["ALGORITHM"]],
            audience=settings.AUTH_JWT["AUDIENCE"],
            issuer=settings.AUTH_JWT["ISSUER"],
        )

    def _encode_payload(self, payload: dict, secret: str | None = None) -> str:
        return jwt.encode(
            payload,
            secret or settings.AUTH_JWT["SECRET"],
            algorithm=settings.AUTH_JWT["ALGORITHM"],
        )

    def test_access_token_contains_required_claims_and_lifetime(self):
        token = issue_access_token(self.user)
        payload = self._decode_payload(token)

        self.assertEqual(payload["sub"], str(self.user.id))
        self.assertEqual(payload["typ"], "access")
        self.assertEqual(payload["iss"], settings.AUTH_JWT["ISSUER"])
        self.assertEqual(payload["aud"], settings.AUTH_JWT["AUDIENCE"])
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)
        self.assertTrue(payload["jti"])
        self.assertEqual(
            payload["exp"] - payload["iat"],
            settings.AUTH_JWT["ACCESS_TOKEN_TTL_SECONDS"],
        )

    def test_decode_returns_typed_claims(self):
        token = issue_access_token(self.user)

        claims = decode_access_token(token)

        self.assertEqual(claims.user_id, self.user.id)
        self.assertEqual(claims.payload["typ"], "access")
        self.assertTrue(claims.jti)
        self.assertLess(claims.issued_at, claims.expires_at)
        self.assertEqual(
            (claims.expires_at - claims.issued_at).total_seconds(),
            settings.AUTH_JWT["ACCESS_TOKEN_TTL_SECONDS"],
        )

    def test_access_tokens_have_unique_jti(self):
        first = decode_access_token(issue_access_token(self.user))
        second = decode_access_token(issue_access_token(self.user))

        self.assertNotEqual(first.jti, second.jti)

    def test_expired_access_token_is_rejected(self):
        token = issue_access_token(self.user, ttl_seconds=-1)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_tampered_access_token_is_rejected(self):
        token = issue_access_token(self.user)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(f"{token}x")

    def test_access_token_signed_with_wrong_secret_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        token = self._encode_payload(
            payload,
            secret="wrong-secret-that-is-long-enough-for-hs256-testing",
        )

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_wrong_token_type_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        payload["typ"] = "refresh"
        token = self._encode_payload(payload)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_wrong_audience_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        payload["aud"] = "https://evil.example.com"
        token = self._encode_payload(payload)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_wrong_issuer_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        payload["iss"] = "https://evil.example.com"
        token = self._encode_payload(payload)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_missing_required_claim_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        payload.pop("jti")
        token = self._encode_payload(payload)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_non_uuid_subject_is_rejected(self):
        payload = self._decode_payload(issue_access_token(self.user))
        payload["sub"] = "not-a-uuid"
        token = self._encode_payload(payload)

        with self.assertRaises(InvalidAccessToken):
            decode_access_token(token)

    def test_malformed_token_is_rejected(self):
        with self.assertRaises(InvalidAccessToken):
            decode_access_token("not-a-jwt")


class RefreshTokenHelperTests(TestCase):
    def test_generated_refresh_token_is_urlsafe_and_32_bytes(self):
        token = generate_refresh_token()

        self.assertEqual(len(token), 43)
        self.assertNotIn("=", token)
        self.assertTrue(all(char.isalnum() or char in "-_" for char in token))

    def test_hash_is_sha256_hex(self):
        token = generate_refresh_token()
        digest = hash_refresh_token(token)

        self.assertEqual(len(digest), 64)
        int(digest, 16)
        self.assertNotEqual(digest, token)

    def test_hashes_are_stable(self):
        token = generate_refresh_token()

        self.assertEqual(hash_refresh_token(token), hash_refresh_token(token))
