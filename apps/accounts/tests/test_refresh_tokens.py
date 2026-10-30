from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import RefreshToken, User
from apps.accounts.tokens import (
    InvalidRefreshToken,
    hash_refresh_token,
    issue_token_pair,
    revoke_all_refresh_tokens,
    revoke_refresh_family,
    rotate_refresh_token,
)


class RefreshTokenRotationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="correct horse battery staple",
        )

    def test_issue_stores_only_hash_and_returns_opaque_token(self):
        pair = issue_token_pair(self.user)

        self.assertEqual(len(pair.refresh_token), 43)
        self.assertFalse(
            RefreshToken.objects.filter(token_hash=pair.refresh_token).exists()
        )

        stored = RefreshToken.objects.get(user=self.user)
        self.assertEqual(stored.token_hash, hash_refresh_token(pair.refresh_token))
        self.assertNotEqual(stored.token_hash, pair.refresh_token)
        self.assertIsNone(stored.revoked_at)
        self.assertGreater(
            stored.expires_at,
            timezone.now() + timedelta(days=29),
        )

    def test_second_issue_revokes_the_first_family(self):
        first = issue_token_pair(self.user)
        first_row = RefreshToken.objects.get(user=self.user)

        second = issue_token_pair(self.user)
        first_row.refresh_from_db()

        self.assertIsNotNone(first_row.revoked_at)
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(first.refresh_token)

        # Second family remains valid.
        rotated = rotate_refresh_token(second.refresh_token)
        self.assertTrue(rotated.refresh_token)

    def test_one_active_family_remains_after_two_logins(self):
        first = issue_token_pair(self.user)
        second = issue_token_pair(self.user)

        active = RefreshToken.objects.filter(revoked_at__isnull=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(
            active.get().token_hash,
            hash_refresh_token(second.refresh_token),
        )
        self.assertNotEqual(
            active.get().token_hash,
            hash_refresh_token(first.refresh_token),
        )

    def test_rotation_revokes_old_token_and_links_new_token(self):
        first = issue_token_pair(self.user)
        old = RefreshToken.objects.get(user=self.user)

        second = rotate_refresh_token(first.refresh_token)
        old.refresh_from_db()
        new = RefreshToken.objects.get(pk=old.replaced_by_id)

        self.assertIsNotNone(old.revoked_at)
        self.assertEqual(new.family_id, old.family_id)
        self.assertEqual(new.token_hash, hash_refresh_token(second.refresh_token))
        self.assertIsNone(new.revoked_at)
        self.assertGreater(new.expires_at, old.expires_at)

    def test_rotated_token_is_rejected(self):
        first = issue_token_pair(self.user)
        rotate_refresh_token(first.refresh_token)

        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(first.refresh_token)

    def test_reuse_revokes_the_entire_family(self):
        first = issue_token_pair(self.user)
        second = rotate_refresh_token(first.refresh_token)

        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(first.refresh_token)

        # Revocation commits before the error is raised.
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(second.refresh_token)
        self.assertEqual(
            RefreshToken.objects.filter(revoked_at__isnull=True).count(),
            0,
        )

    def test_sliding_expiry_extends_from_rotation_time(self):
        start = timezone.now().replace(microsecond=0)
        first = issue_token_pair(self.user, now=start)
        old = RefreshToken.objects.get(user=self.user)

        rotation_time = start + timedelta(days=10)
        second = rotate_refresh_token(first.refresh_token, now=rotation_time)
        old.refresh_from_db()
        new = RefreshToken.objects.get(pk=old.replaced_by_id)

        expected = rotation_time + timedelta(
            seconds=settings.AUTH_REFRESH_TOKEN_TTL_SECONDS
        )
        self.assertEqual(new.expires_at, expected)
        self.assertEqual(second.refresh_expires_at, expected)

    def test_expired_token_is_rejected(self):
        pair = issue_token_pair(self.user, refresh_ttl_seconds=-1)

        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(pair.refresh_token)

    def test_unknown_token_is_rejected(self):
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token("unknown-token")

    def test_blank_token_is_rejected(self):
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token("")

    def test_inactive_user_cannot_rotate(self):
        pair = issue_token_pair(self.user)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(pair.refresh_token)

        self.assertEqual(
            RefreshToken.objects.filter(revoked_at__isnull=True).count(),
            0,
        )

    def test_logout_revokes_family_and_is_idempotent(self):
        pair = issue_token_pair(self.user)

        revoke_refresh_family(pair.refresh_token)
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(pair.refresh_token)

        # Repeated logout and unknown tokens are no-ops.
        revoke_refresh_family(pair.refresh_token)
        revoke_refresh_family("unknown-token")
        revoke_refresh_family("")

    def test_revoke_all_refresh_tokens(self):
        pair = issue_token_pair(self.user)

        count = revoke_all_refresh_tokens(self.user)

        self.assertEqual(count, 1)
        with self.assertRaises(InvalidRefreshToken):
            rotate_refresh_token(pair.refresh_token)

    def test_refresh_token_string_does_not_leak_hash(self):
        pair = issue_token_pair(self.user)
        stored = RefreshToken.objects.get(user=self.user)

        self.assertNotIn(stored.token_hash, str(stored))
        self.assertNotIn(pair.refresh_token, str(stored))
