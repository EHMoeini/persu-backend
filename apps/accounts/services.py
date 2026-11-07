"""Authentication business logic."""

from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password as verify_password
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction

from .models import User
from .tokens import TokenPair, issue_token_pair


class InvalidCredentials(Exception):
    """The phone/password combination is not valid."""


class PhoneAlreadyRegistered(Exception):
    """The normalized phone number already belongs to an account."""


class InvalidOtpCode(Exception):
    """The supplied OTP code is not the configured mock code."""


# Equalizes timing when the phone number is unknown.
_DUMMY_PASSWORD_HASH = make_password("persu-dummy-password-not-a-real-account")


def phone_exists(phone_e164: str) -> bool:
    return User.objects.filter(phone_e164=phone_e164).exists()


def authenticate_user(phone_e164: str, password: str) -> User:
    user = User.objects.filter(phone_e164=phone_e164).first()

    if user is None or not user.is_active or not user.has_usable_password():
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise InvalidCredentials

    if not user.check_password(password):
        raise InvalidCredentials

    return user


def login_user(phone_e164: str, password: str) -> tuple[User, TokenPair]:
    user = authenticate_user(phone_e164, password)
    return user, issue_token_pair(user)


def register_user(
    phone_e164: str,
    password: str,
    *,
    full_name: str = "",
) -> tuple[User, TokenPair]:
    nick_name = full_name.strip() if isinstance(full_name, str) else ""
    try:
        # Savepoint keeps the outer transaction usable on duplicate phones.
        with transaction.atomic():
            user = User.objects.create_user(
                phone_e164=phone_e164,
                password=password,
                nick_name=nick_name,
            )
    except IntegrityError as exc:
        raise PhoneAlreadyRegistered from exc

    return user, issue_token_pair(user)


def verify_otp(phone_e164: str, code: str) -> tuple[User, TokenPair]:
    """Validate the mocked OTP code and issue a real token pair.

    A user is created for an unknown phone number so OTP verification can also
    act as a passwordless registration flow. The code check is intentionally
    mocked; the access and refresh tokens are produced by the normal token
    service.
    """

    if not isinstance(code, str) or not secrets.compare_digest(
        code,
        settings.AUTH_OTP_MOCK_CODE,
    ):
        raise InvalidOtpCode

    user = User.objects.filter(phone_e164=phone_e164).first()
    if user is None:
        try:
            # Savepoint keeps the outer transaction usable on a concurrent
            # create for the same phone number.
            with transaction.atomic():
                user = User.objects.create_user(phone_e164=phone_e164)
        except IntegrityError:
            user = User.objects.get(phone_e164=phone_e164)

    if not user.is_active:
        raise InvalidOtpCode

    return user, issue_token_pair(user)
