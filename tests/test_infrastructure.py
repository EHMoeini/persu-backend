"""One smoke test proving pytest-django, the DB, factories, and auth clients work."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_pytest_django_factories_and_auth_client(user, auth_client):
    assert user.pk is not None
    assert user.phone_e164.startswith("+")
    assert user.check_password("correct horse battery staple")
    assert isinstance(auth_client, APIClient)
