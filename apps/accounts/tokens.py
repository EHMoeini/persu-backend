"""Access JWT and refresh-token services."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import RefreshToken, User


class InvalidAccessToken(Exception):
    """Raised when an access token is invalid or expired."""


class InvalidRefreshToken(Exception):
    """Raised when a refresh token is invalid, expired, or reused."""


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    jti: str
    issued_at: datetime
    expires_at: datetime
    payload: dict


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


def _utc_now(value: datetime | None = None) -> datetime:
    if value is None:
        return timezone.now()
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value.astimezone(dt_timezone.utc)


def _access_ttl(ttl_seconds: int | None) -> int:
    if ttl_seconds is None:
        return int(settings.AUTH_JWT["ACCESS_TOKEN_TTL_SECONDS"])
    return int(ttl_seconds)


def _refresh_ttl(ttl_seconds: int | None) -> int:
    if ttl_seconds is None:
        return int(settings.AUTH_REFRESH_TOKEN_TTL_SECONDS)
    return int(ttl_seconds)


def issue_access_token(
    user: User,
    *,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
) -> str:
    """Issue an access JWT."""
    issued_at = _utc_now(now)
    ttl = _access_ttl(ttl_seconds)
    iat = int(issued_at.timestamp())

    payload = {
        "sub": str(user.pk),
        "typ": "access",
        "iss": settings.AUTH_JWT["ISSUER"],
        "aud": settings.AUTH_JWT["AUDIENCE"],
        "iat": iat,
        "exp": iat + ttl,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.AUTH_JWT["SECRET"],
        algorithm=settings.AUTH_JWT["ALGORITHM"],
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    """Validate an access JWT and return its claims."""
    if not isinstance(token, str) or not token:
        raise InvalidAccessToken("Invalid access token.")

    try:
        payload = jwt.decode(
            token,
            settings.AUTH_JWT["SECRET"],
            algorithms=[settings.AUTH_JWT["ALGORITHM"]],
            audience=settings.AUTH_JWT["AUDIENCE"],
            issuer=settings.AUTH_JWT["ISSUER"],
            options={
                "require": ["sub", "typ", "iss", "aud", "iat", "exp", "jti"],
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidAccessToken("Invalid or expired access token.") from exc

    if payload.get("typ") != "access":
        raise InvalidAccessToken("Invalid token type.")

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("Invalid token subject.") from exc

    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise InvalidAccessToken("Invalid token identifier.")

    try:
        issued_at = datetime.fromtimestamp(
            float(payload["iat"]), tz=dt_timezone.utc
        )
        expires_at = datetime.fromtimestamp(
            float(payload["exp"]), tz=dt_timezone.utc
        )
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise InvalidAccessToken("Invalid token timestamps.") from exc

    return AccessTokenClaims(
        user_id=user_id,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
        payload=payload,
    )


def generate_refresh_token() -> str:
    """Generate a 32-byte base64url refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """Hash a refresh token for storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _revoke_family(family_id: uuid.UUID, now: datetime) -> int:
    return RefreshToken.objects.filter(
        family_id=family_id,
        revoked_at__isnull=True,
    ).update(revoked_at=now)


def _revoke_all_for_user(user: User, now: datetime) -> int:
    return RefreshToken.objects.filter(
        user=user,
        revoked_at__isnull=True,
    ).update(revoked_at=now)


def issue_token_pair(
    user: User,
    *,
    revoke_existing: bool = True,
    now: datetime | None = None,
    refresh_ttl_seconds: int | None = None,
) -> TokenPair:
    """Create a token pair and revoke the user's previous family."""
    issued_at = _utc_now(now)
    ttl = _refresh_ttl(refresh_ttl_seconds)

    with transaction.atomic():
        if revoke_existing:
            # Lock the user so concurrent logins leave one active family.
            user = User.objects.select_for_update().get(pk=user.pk)
            _revoke_all_for_user(user, issued_at)

        raw_refresh_token = generate_refresh_token()
        refresh_token = RefreshToken.objects.create(
            user=user,
            family_id=uuid.uuid4(),
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=issued_at + timedelta(seconds=ttl),
        )
        access_token = issue_access_token(user, now=issued_at)

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        refresh_expires_at=refresh_token.expires_at,
    )


def rotate_refresh_token(
    raw_token: str,
    *,
    now: datetime | None = None,
    refresh_ttl_seconds: int | None = None,
) -> TokenPair:
    """Rotate a refresh token; reuse revokes the whole family."""
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise InvalidRefreshToken("Invalid refresh token.")

    issued_at = _utc_now(now)
    ttl = _refresh_ttl(refresh_ttl_seconds)
    token_hash = hash_refresh_token(raw_token)
    outcome = "invalid"
    result: TokenPair | None = None

    with transaction.atomic():
        token = (
            RefreshToken.objects.select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )

        if token is None:
            raise InvalidRefreshToken("Invalid refresh token.")

        if token.revoked_at is not None:
            _revoke_family(token.family_id, issued_at)
            outcome = "reuse"
        elif token.expires_at <= issued_at:
            outcome = "expired"
        elif not token.user.is_active:
            _revoke_family(token.family_id, issued_at)
            outcome = "inactive"
        else:
            raw_refresh_token = generate_refresh_token()
            new_token = RefreshToken.objects.create(
                user=token.user,
                family_id=token.family_id,
                token_hash=hash_refresh_token(raw_refresh_token),
                expires_at=issued_at + timedelta(seconds=ttl),
            )
            token.revoked_at = issued_at
            token.replaced_by = new_token
            token.save(update_fields=["revoked_at", "replaced_by"])

            outcome = "rotated"
            result = TokenPair(
                access_token=issue_access_token(token.user, now=issued_at),
                refresh_token=raw_refresh_token,
                refresh_expires_at=new_token.expires_at,
            )

    if outcome != "rotated" or result is None:
        raise InvalidRefreshToken("Invalid or expired refresh token.")

    return result


def revoke_refresh_family(
    raw_token: str,
    *,
    now: datetime | None = None,
) -> None:
    """Revoke a refresh-token family; safe to retry."""
    if not isinstance(raw_token, str) or not raw_token.strip():
        return

    issued_at = _utc_now(now)
    token_hash = hash_refresh_token(raw_token)

    with transaction.atomic():
        token = (
            RefreshToken.objects.select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )
        if token is not None:
            _revoke_family(token.family_id, issued_at)


def revoke_all_refresh_tokens(
    user: User,
    *,
    now: datetime | None = None,
) -> int:
    """Revoke all active refresh tokens for a user."""
    issued_at = _utc_now(now)
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        return _revoke_all_for_user(locked_user, issued_at)
