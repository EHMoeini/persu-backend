import uuid

from django.contrib.auth.hashers import identify_hasher
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User

PHONE = "+12024561111"
PASSWORD = "correct horse battery staple"


class UserModelTests(TestCase):
    def test_create_user_hashes_password_with_argon2(self):
        user = User.objects.create_user(phone_e164=PHONE, password=PASSWORD)

        self.assertIsInstance(user.id, uuid.UUID)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("argon2$"))
        self.assertIn("$argon2id$", user.password)
        self.assertEqual(identify_hasher(user.password).algorithm, "argon2")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password("wrong password"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_phone_is_unique_at_database_level(self):
        User.objects.create_user(phone_e164=PHONE, password=PASSWORD)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(phone_e164=PHONE, password="another")

    def test_manager_rejects_non_e164_phone(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(phone_e164="2024561111", password=PASSWORD)

    def test_manager_allows_unusable_password(self):
        user = User.objects.create_user(phone_e164=PHONE)

        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.check_password(""))

    def test_create_superuser_sets_required_flags(self):
        user = User.objects.create_superuser(phone_e164=PHONE, password=PASSWORD)

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_string_representation_masks_phone(self):
        user = User.objects.create_user(phone_e164=PHONE, password=PASSWORD)

        self.assertEqual(str(user), "***1111")
        self.assertNotIn(PHONE, str(user))
