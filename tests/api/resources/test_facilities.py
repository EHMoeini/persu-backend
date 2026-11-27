"""Contract tests for the public facility search API."""

from __future__ import annotations

import pytest

from apps.resources.models import Facility

pytestmark = pytest.mark.django_db

LISTING_FIELDS = {
    "id",
    "name",
    "description",
    "category",
    "type",
    "location",
    "price",
    "picture",
    "rating",
    "availability",
}


def test_search_returns_listing_details(api_client):
    Facility.objects.create(
        name="Sunset Yoga Studio",
        description="Small-group yoga and meditation classes.",
        category="Fitness",
        type="Yoga Studio",
        location="West Side",
        price="280000.00",
        picture="https://picsum.photos/seed/yoga-contract/800/600",
        rating="4.7",
        availability=False,
    )

    response = api_client.get("/api/facilities", {"q": "meditation"})

    assert response.status_code == 200
    facilities = response.json()["facilities"]
    assert len(facilities) == 1
    facility = facilities[0]
    assert set(facility) == LISTING_FIELDS
    assert facility["name"] == "Sunset Yoga Studio"
    assert facility["price"] == 280000
    assert facility["rating"] == 4.7
    assert facility["availability"] is False


def test_search_without_matches_returns_an_empty_list(api_client):
    response = api_client.get("/api/facilities", {"q": "helicopter"})

    assert response.status_code == 200
    assert response.json() == {"facilities": []}


def test_blank_search_returns_every_listing(api_client):
    Facility.objects.create(name="First Facility")
    Facility.objects.create(name="Second Facility")

    response = api_client.get("/api/facilities", {"q": "   "})

    assert response.status_code == 200
    assert len(response.json()["facilities"]) == 2
