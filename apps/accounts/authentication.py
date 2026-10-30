"""Bearer access-token authentication for DRF."""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import User
from .tokens import InvalidAccessToken, decode_access_token


class BearerAuthentication(BaseAuthentication):
    """Authenticate ``Authorization: Bearer <token>`` headers."""

    keyword = b"bearer"
    max_token_length = 4096

    def authenticate(self, request):
        parts = get_authorization_header(request).split()

        if not parts:
            return None

        if parts[0].lower() != self.keyword:
            return None

        if len(parts) != 2:
            raise AuthenticationFailed("Invalid authorization header.")

        try:
            raw_token = parts[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid authorization header.") from exc

        if len(raw_token) > self.max_token_length:
            raise AuthenticationFailed("Invalid access token.")

        try:
            claims = decode_access_token(raw_token)
        except InvalidAccessToken as exc:
            raise AuthenticationFailed("Invalid or expired access token.") from exc

        try:
            user = User.objects.get(pk=claims.user_id)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid access token.") from exc

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        return user, claims

    def authenticate_header(self, request) -> str:
        # Return a challenge so DRF responds with 401 instead of 403.
        return 'Bearer realm="api"'
