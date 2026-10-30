from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager
from .phone import mask_phone, validate_phone_e164


class User(AbstractBaseUser, PermissionsMixin):
    """Application user identified by a unique E.164 phone number."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_e164 = models.CharField(
        _("phone number"),
        max_length=16,
        unique=True,
        validators=[validate_phone_e164],
        help_text="Phone number normalized to E.164 format.",
    )
    # Django expects this attribute to be named password.
    password = models.CharField(
        _("password hash"), max_length=128, db_column="password_hash"
    )
    nick_name = models.CharField(_("nickname"), max_length=64, blank=True, default="")
    avatar = models.URLField(_("avatar"), max_length=500, blank=True, default="")
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_e164"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"], name="users_created_at_idx"),
        ]

    def __str__(self) -> str:
        return mask_phone(self.phone_e164)

    def get_full_name(self) -> str:
        return self.nick_name or self.phone_e164

    def get_short_name(self) -> str:
        return self.nick_name or self.phone_e164


class RefreshToken(models.Model):
    """Hashed refresh token belonging to a rotation family."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    family_id = models.UUIDField(default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refresh_tokens"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["family_id", "revoked_at"],
                name="refresh_family_idx",
            ),
            models.Index(
                fields=["user", "family_id"],
                name="refresh_user_family_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="refresh_expires_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"RefreshToken({self.id})"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
