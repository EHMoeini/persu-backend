from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager

from .phone import E164_PATTERN


class UserManager(BaseUserManager):
    """Manager for users identified by an E.164 phone number."""

    use_in_migrations = True

    def create_user(self, phone_e164: str, password: str | None = None, **extra_fields):
        if not phone_e164:
            raise ValueError("The phone number is required.")

        phone_e164 = str(phone_e164).strip()
        if not E164_PATTERN.fullmatch(phone_e164):
            raise ValueError("Phone numbers must be normalized to E.164 format.")

        extra_fields.setdefault("is_active", True)

        user = self.model(phone_e164=phone_e164, **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, phone_e164: str, password: str | None = None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone_e164, password, **extra_fields)
