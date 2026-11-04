"""Factory Boy factories for API tests."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.models import RefreshToken, User

DEFAULT_PASSWORD = "correct horse battery staple"


class UserFactory(factory.django.DjangoModelFactory):
    """Active user with a valid, unique E.164 phone number."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    class Params:
        inactive = factory.Trait(is_active=False)
        staff = factory.Trait(is_staff=True)

    id = factory.LazyFunction(uuid.uuid4)
    phone_e164 = factory.Sequence(lambda n: f"+1202555{n:04d}")
    nick_name = ""
    avatar = ""
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save(update_fields=["password"])


class RefreshTokenFactory(factory.django.DjangoModelFactory):
    """Persisted refresh-token row; the raw token is not retained."""

    class Meta:
        model = RefreshToken

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    family_id = factory.LazyFunction(uuid.uuid4)
    token_hash = factory.LazyFunction(
        lambda: hashlib.sha256(secrets.token_urlsafe(32).encode("utf-8")).hexdigest()
    )
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30)
    )
    revoked_at = None
