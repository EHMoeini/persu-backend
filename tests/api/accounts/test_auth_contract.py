"""Contract tests for the auth changes requested by the frontend team."""

from __future__ import annotations

import pytest
from django.conf import settings

from apps.accounts.models import RefreshToken, User
from apps.accounts.tokens import decode_access_token
from tests.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

IRAN_E164 = "+989123456789"
CUSTOM_HEADERS = (
    "x-app-version",
    "x-platform",
    "x-client-locale",
    "x-seconds-from-utc",
)


def _national_number(user: User) -> str:
    return user.phone_e164.removeprefix("+1")


def _login(api_client, user: User):
    return api_client.post(
        "/auth/login",
        {
            "countryCode": "US",
            "phone": _national_number(user),
            "password": DEFAULT_PASSWORD,
        },
        format="json",
    )


def test_public_auth_endpoints_do_not_return_500(api_client, user):
    check = api_client.post(
        "/auth/check",
        {"countryCode": "US", "phone": _national_number(user)},
        format="json",
    )
    assert check.status_code == 200

    login = _login(api_client, user)
    assert login.status_code == 200
    tokens = login.json()

    refresh = api_client.post(
        "/auth/refresh",
        {"refreshToken": tokens["refreshToken"]},
        format="json",
    )
    assert refresh.status_code == 200

    rotated = refresh.json()
    logout = api_client.post(
        "/auth/logout",
        {"refreshToken": rotated["refreshToken"]},
        format="json",
    )
    assert logout.status_code == 204


def test_iran_national_number_is_normalized_to_e164(api_client):
    User.objects.create_user(
        phone_e164=IRAN_E164,
        password=DEFAULT_PASSWORD,
    )

    response = api_client.post(
        "/auth/check",
        {"countryCode": "IR", "phone": "09123456789"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"exists": True}


def test_iran_national_number_can_log_in(api_client):
    user = User.objects.create_user(
        phone_e164=IRAN_E164,
        password=DEFAULT_PASSWORD,
    )

    response = api_client.post(
        "/auth/login",
        {
            "countryCode": "IR",
            "phone": "09123456789",
            "password": DEFAULT_PASSWORD,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.id)
    assert response.json()["user"]["phone"] == IRAN_E164


def test_register_accepts_full_name(api_client):
    response = api_client.post(
        "/auth/register",
        {
            "countryCode": "IR",
            "phone": "09123456789",
            "password": DEFAULT_PASSWORD,
            "fullName": "Ada Lovelace",
        },
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["phone"] == IRAN_E164
    assert data["user"]["nickName"] == "Ada Lovelace"

    user = User.objects.get(phone_e164=IRAN_E164)
    assert user.nick_name == "Ada Lovelace"


def test_otp_verify_returns_real_token_pair_and_user(api_client, user):
    response = api_client.post(
        "/auth/otp/verify",
        {
            "countryCode": "US",
            "phone": _national_number(user),
            "code": settings.AUTH_OTP_MOCK_CODE,
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"accessToken", "refreshToken", "user"}
    assert data["user"]["id"] == str(user.id)
    assert decode_access_token(data["accessToken"]).user_id == user.id
    assert (
        RefreshToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
        ).count()
        == 1
    )


def test_otp_verify_creates_the_user_when_phone_is_unknown(api_client):
    response = api_client.post(
        "/auth/otp/verify",
        {
            "countryCode": "IR",
            "phone": "09123456789",
            "code": settings.AUTH_OTP_MOCK_CODE,
        },
        format="json",
    )

    assert response.status_code == 200
    user = User.objects.get(phone_e164=IRAN_E164)
    assert response.json()["user"]["id"] == str(user.id)
    assert not user.has_usable_password()


def test_otp_verify_rejects_a_wrong_code(api_client, user):
    response = api_client.post(
        "/auth/otp/verify",
        {
            "countryCode": "US",
            "phone": _national_number(user),
            "code": "not-the-code",
        },
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_otp"
    assert not RefreshToken.objects.filter(user=user).exists()


def test_auth_preflight_allows_custom_frontend_headers(api_client):
    origin = settings.CORS_ALLOWED_ORIGINS[0]
    response = api_client.options(
        "/auth/check",
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
            "authorization,content-type," + ",".join(CUSTOM_HEADERS)
        ),
    )

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == origin

    allowed_headers = response["Access-Control-Allow-Headers"].lower()
    for header in ("authorization", "content-type", *CUSTOM_HEADERS):
        assert header in allowed_headers
