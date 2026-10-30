from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.permissions import IsAuthenticatedUser, IsOwner


class IsAuthenticatedUserTests(TestCase):
    def test_active_authenticated_user_is_allowed(self):
        user = User.objects.create_user(
            phone_e164="+12024561111",
            password="password",
        )
        request = SimpleNamespace(user=user)

        self.assertTrue(IsAuthenticatedUser().has_permission(request, None))

    def test_anonymous_user_is_denied(self):
        request = SimpleNamespace(user=AnonymousUser())

        self.assertFalse(IsAuthenticatedUser().has_permission(request, None))

    def test_inactive_user_is_denied(self):
        user = User.objects.create_user(
            phone_e164="+12024561111",
            password="password",
        )
        user.is_active = False
        request = SimpleNamespace(user=user)

        self.assertFalse(IsAuthenticatedUser().has_permission(request, None))


class IsOwnerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_e164="+12024561111",
            password="password",
        )
        self.request = SimpleNamespace(user=self.user)

    def test_owner_is_allowed(self):
        obj = SimpleNamespace(user_id=self.user.id)

        self.assertTrue(
            IsOwner().has_object_permission(self.request, None, obj)
        )

    def test_non_owner_is_denied(self):
        obj = SimpleNamespace(user_id="00000000-0000-0000-0000-000000000000")

        self.assertFalse(
            IsOwner().has_object_permission(self.request, None, obj)
        )

    def test_missing_owner_is_denied(self):
        obj = SimpleNamespace()

        self.assertFalse(
            IsOwner().has_object_permission(self.request, None, obj)
        )

    def test_custom_owner_field(self):
        class ProfileOwnerPermission(IsOwner):
            owner_field = "profile_user_id"

        obj = SimpleNamespace(profile_user_id=self.user.id)

        self.assertTrue(
            ProfileOwnerPermission().has_object_permission(self.request, None, obj)
        )
