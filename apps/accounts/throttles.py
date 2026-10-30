"""Throttle auth routes by phone or refresh token."""

from __future__ import annotations

import hashlib

from rest_framework.exceptions import ParseError
from rest_framework.throttling import ScopedRateThrottle

from .phone import InvalidPhoneNumber, normalize_phone


class AuthScopedRateThrottle(ScopedRateThrottle):
    def get_cache_key(self, request, view):
        if not self.scope:
            return None

        try:
            data = request.data
        except ParseError:
            # Keep malformed JSON as invalid_json, not validation_error.
            raise
        except Exception:
            data = None

        subject: str | None = None

        if hasattr(data, "get"):
            refresh_token = data.get("refreshToken")
            if refresh_token:
                subject = f"refresh:{refresh_token}"
            else:
                phone = data.get("phone")
                if phone:
                    country_code = str(data.get("countryCode", ""))
                    try:
                        normalized = normalize_phone(country_code, str(phone))
                    except InvalidPhoneNumber:
                        # Invalid numbers fall back to the IP bucket.
                        normalized = None
                    if normalized:
                        subject = f"phone:{normalized}"

        if subject is None:
            subject = f"ip:{self.get_ident(request)}"

        ident = hashlib.sha256(subject.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
