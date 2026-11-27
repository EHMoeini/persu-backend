from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.resources.mock_data import (
    MOCK_FACILITIES,
    RETIRED_MOCK_FACILITY_KEYS,
    mock_facility_id,
)
from apps.resources.models import Facility


class SeedFacilitiesCommandTests(APITestCase):
    def seed(self, **options) -> str:
        output = StringIO()
        call_command("seed_facilities", stdout=output, **options)
        return output.getvalue()

    def test_seed_creates_realistic_listings(self):
        self.seed()

        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))
        self.assertGreaterEqual(
            Facility.objects.values("category").distinct().count(),
            5,
        )

        football = Facility.objects.get(name="زمین فوتبال ملی آزادی")
        self.assertTrue(football.description)
        self.assertEqual(football.category, "Football")
        self.assertEqual(football.type, "زمین فوتبال")
        self.assertEqual(football.price, 1800000)
        self.assertTrue(football.picture.startswith("https://"))
        self.assertGreaterEqual(football.rating, 1)
        self.assertLessEqual(football.rating, 5)
        self.assertTrue(football.availability)

    def test_seed_is_idempotent(self):
        self.seed()
        first_ids = set(Facility.objects.values_list("id", flat=True))

        self.seed()

        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))
        self.assertEqual(
            set(Facility.objects.values_list("id", flat=True)),
            first_ids,
        )

    def test_seed_removes_retired_english_mock_listings(self):
        retired_id = mock_facility_id("azadi-national-football-field")
        Facility.objects.create(
            pk=retired_id,
            name="Azadi National Football Field",
            type="Soccer Field",
            location="Azadi Sports Complex, Tehran",
        )

        self.seed()

        self.assertFalse(Facility.objects.filter(pk=retired_id).exists())
        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))

    def test_if_empty_replaces_an_english_mock_seed(self):
        retired_id = mock_facility_id(RETIRED_MOCK_FACILITY_KEYS[0])
        Facility.objects.create(
            pk=retired_id,
            name="Azadi National Football Field",
            type="Soccer Field",
            location="Azadi Sports Complex, Tehran",
        )

        output = self.seed(if_empty=True)

        self.assertNotIn("skipping mock seed", output)
        self.assertFalse(Facility.objects.filter(pk=retired_id).exists())
        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))

    def test_seed_does_not_modify_real_facilities(self):
        real = Facility.objects.create(
            name="Community Sports Hall",
            type="Sports Hall",
            location="Local Neighborhood",
        )

        self.seed()

        real.refresh_from_db()
        self.assertEqual(real.name, "Community Sports Hall")
        self.assertEqual(real.type, "Sports Hall")
        self.assertEqual(real.location, "Local Neighborhood")

    def test_if_empty_seeds_an_empty_database(self):
        self.seed(if_empty=True)

        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))

    def test_if_empty_extends_an_older_mock_seed(self):
        self.seed()
        missing_name = "زمین بسکتبال منطقه شش"
        Facility.objects.filter(name=missing_name).delete()
        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES) - 1)

        output = self.seed(if_empty=True)

        self.assertNotIn("skipping mock seed", output)
        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))
        self.assertTrue(
            Facility.objects.filter(name=missing_name).exists()
        )

    def test_if_empty_skips_a_database_with_real_facilities(self):
        real = Facility.objects.create(
            name="Community Sports Hall",
            type="Sports Hall",
            location="Local Neighborhood",
        )

        output = self.seed(if_empty=True)

        self.assertIn("skipping mock seed", output)
        self.assertEqual(Facility.objects.count(), 1)
        self.assertTrue(Facility.objects.filter(pk=real.pk).exists())
        self.assertFalse(
            Facility.objects.filter(
                name="زمین فوتبال ملی آزادی"
            ).exists()
        )

    def test_if_empty_removes_retired_english_rows_with_real_data(self):
        retired_id = mock_facility_id("azadi-national-football-field")
        Facility.objects.create(
            pk=retired_id,
            name="Azadi National Football Field",
            type="Soccer Field",
            location="Azadi Sports Complex, Tehran",
        )
        real = Facility.objects.create(
            name="Community Sports Hall",
            type="Sports Hall",
            location="Local Neighborhood",
        )

        output = self.seed(if_empty=True)

        self.assertIn("retired mock listing", output)
        self.assertIn("skipping mock seed", output)
        self.assertFalse(Facility.objects.filter(pk=retired_id).exists())
        self.assertTrue(Facility.objects.filter(pk=real.pk).exists())
        self.assertEqual(Facility.objects.count(), 1)

    def test_if_empty_does_not_extend_an_older_mock_seed_with_real_data(self):
        self.seed()
        real = Facility.objects.create(
            name="Community Sports Hall",
            type="Sports Hall",
            location="Local Neighborhood",
        )
        missing_name = "زمین بسکتبال منطقه شش"
        Facility.objects.filter(name=missing_name).delete()

        output = self.seed(if_empty=True)

        self.assertIn("skipping mock seed", output)
        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES))
        self.assertTrue(Facility.objects.filter(pk=real.pk).exists())
        self.assertFalse(
            Facility.objects.filter(name=missing_name).exists()
        )

    def test_reset_only_deletes_seeded_mock_listings(self):
        real = Facility.objects.create(
            name="Community Sports Hall",
            type="Sports Hall",
            location="Local Neighborhood",
        )
        self.seed()

        self.seed(reset=True)

        self.assertEqual(Facility.objects.count(), len(MOCK_FACILITIES) + 1)
        self.assertTrue(Facility.objects.filter(pk=real.pk).exists())

    def test_every_seeded_listing_exposes_the_required_api_fields(self):
        self.seed()

        response = self.client.get("/api/facilities")

        self.assertEqual(response.status_code, 200)
        facilities = response.json()["facilities"]
        self.assertEqual(len(facilities), len(MOCK_FACILITIES))
        for facility in facilities:
            self.assertTrue(facility["name"])
            self.assertTrue(facility["description"])
            self.assertTrue(facility["category"])
            self.assertGreater(facility["price"], 0)
            self.assertTrue(facility["picture"].startswith("https://"))
            self.assertGreaterEqual(facility["rating"], 1)
            self.assertLessEqual(facility["rating"], 5)
            self.assertIsInstance(facility["availability"], bool)

    def test_seed_contains_only_persian_listings(self):
        self.seed()

        facilities = list(Facility.objects.all())

        self.assertEqual(len(facilities), len(MOCK_FACILITIES))
        for facility in facilities:
            self.assertTrue(
                any("\u0600" <= char <= "\u06ff" for char in facility.name)
            )
            self.assertTrue(
                any(
                    "\u0600" <= char <= "\u06ff"
                    for char in facility.description
                )
            )

        self.assertEqual(
            {facility.category for facility in facilities},
            {
                "Football",
                "Swimming",
                "Racket Sports",
                "Fitness",
                "Basketball",
                "Volleyball",
                "Martial Arts",
                "Climbing",
                "Multi-Sport",
            },
        )
        self.assertGreaterEqual(
            Facility.objects.filter(category="Football").count(), 6
        )
        self.assertGreaterEqual(
            Facility.objects.filter(category="Swimming").count(), 4
        )

    def test_seeded_pictures_are_unique_and_not_placeholders(self):
        self.seed()

        pictures = list(Facility.objects.values_list("picture", flat=True))

        self.assertEqual(len(set(pictures)), len(MOCK_FACILITIES))
        self.assertFalse(
            any("picsum.photos" in picture for picture in pictures)
        )
        self.assertTrue(
            all(
                picture.startswith(
                    "https://thumb.wikimedia.org/wikipedia/commons/"
                )
                for picture in pictures
            )
        )

    def test_persian_seeded_listings_are_searchable(self):
        self.seed()

        cases = {
            "بسکتبال": "زمین بسکتبال منطقه شش",
            "یوگا": "استودیو یوگا آرامش",
            "سنگ نوردی": "دیواره سنگ‌نوردی ارس",
        }
        for query, expected_name in cases.items():
            with self.subTest(query=query):
                response = self.client.get("/api/facilities", {"q": query})
                names = [
                    item["name"] for item in response.json()["facilities"]
                ]
                self.assertIn(expected_name, names)

    def test_seeded_listings_are_returned_by_the_search_api(self):
        self.seed()

        response = self.client.get("/api/facilities", {"q": "swimming"})

        self.assertEqual(response.status_code, 200)
        facilities = response.json()["facilities"]
        self.assertEqual(
            {item["name"] for item in facilities},
            {
                "استخر سرپوشیده پارس",
                "استخر المپیک تهران",
                "استخر عمومی مهر",
                "استخر خانوادگی مروارید",
            },
        )
        for facility in facilities:
            self.assertEqual(
                set(facility),
                {
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
                },
            )
