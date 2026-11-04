"""Shared pytest fixtures for the API test suite."""

from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.tokens import issue_access_token, issue_token_pair
from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Keep per-phone/per-token throttle buckets isolated between tests."""

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def inactive_user(db):
    return UserFactory(is_active=False)


@pytest.fixture
def staff_user(db):
    return UserFactory(is_staff=True)


@pytest.fixture
def bearer_token(user):
    return issue_access_token(user)


@pytest.fixture
def token_pair(user):
    return issue_token_pair(user)


def _authenticated_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_access_token(user)}")
    return client


@pytest.fixture
def auth_client(user):
    return _authenticated_client(user)


@pytest.fixture
def other_auth_client(other_user):
    return _authenticated_client(other_user)


@pytest.fixture
def inactive_auth_client(inactive_user):
    # The token is issued deliberately; BearerAuthentication must reject it.
    return _authenticated_client(inactive_user)


@pytest.fixture
def staff_auth_client(staff_user):
    return _authenticated_client(staff_user)


@pytest.fixture
def auth_client_for():
    """Build an authenticated client for any user object on demand."""

    def make(user) -> APIClient:
        return _authenticated_client(user)

    return make
