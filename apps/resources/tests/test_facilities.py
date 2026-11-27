from rest_framework.test import APITestCase

from apps.resources.models import Facility


class FacilitySearchTests(APITestCase):
    def setUp(self):
        self.soccer = Facility.objects.create(
            name="Soccer Field A",
            type="Soccer Field",
            location="North Park",
        )
        self.pool = Facility.objects.create(
            name="Olympic Swimming Pool",
            type="Swimming Pool",
            location="Downtown",
        )
        self.tennis = Facility.objects.create(
            name="Riverside Tennis Court",
            type="Tennis Court",
            location="Riverside",
        )
        self.futsal = Facility.objects.create(
            name="Futsal Court",
            type="Futsal",
            location="East Side",
        )

    def search(self, query: str | None = None):
        params = {} if query is None else {"q": query}
        return self.client.get("/api/facilities", params)

    def names(self, response) -> list[str]:
        return [item["name"] for item in response.json()["facilities"]]

    def test_search_returns_all_for_missing_query(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.names(response),
            [
                "Futsal Court",
                "Olympic Swimming Pool",
                "Riverside Tennis Court",
                "Soccer Field A",
            ],
        )

    def test_search_returns_all_for_blank_query(self):
        for query in ("", "   "):
            response = self.search(query)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["facilities"]), 4)

    def test_partial_name_search_is_case_insensitive(self):
        response = self.search("socc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Soccer Field A"])

        self.assertEqual(self.names(self.search("SOCCER")), ["Soccer Field A"])

    def test_searches_facility_type(self):
        response = self.search("swimming")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Olympic Swimming Pool"])

    def test_searches_location(self):
        response = self.search("riverside")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Riverside Tennis Court"])

    def test_partial_query_can_match_multiple_facilities(self):
        response = self.search("court")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.names(response)),
            {"Futsal Court", "Riverside Tennis Court"},
        )

    def test_search_returns_empty_list_when_nothing_matches(self):
        response = self.search("ice rink")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"facilities": []})

    def test_response_contains_public_listing_fields(self):
        response = self.search("soccer")

        facility = response.json()["facilities"][0]
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
        self.assertEqual(facility["name"], "Soccer Field A")
        self.assertEqual(facility["type"], "Soccer Field")
        self.assertEqual(facility["location"], "North Park")
        self.assertEqual(facility["description"], "")
        self.assertEqual(facility["category"], "")
        self.assertEqual(facility["price"], 0)
        self.assertEqual(facility["picture"], "")
        self.assertEqual(facility["rating"], 0)
        self.assertTrue(facility["availability"])

    def test_response_contains_listing_details(self):
        Facility.objects.create(
            name="Sunset Yoga Studio",
            description="Small-group yoga and meditation classes.",
            category="Fitness",
            type="Yoga Studio",
            location="West Side",
            price="280000.00",
            picture="https://picsum.photos/seed/yoga-test/800/600",
            rating="4.7",
            availability=False,
        )

        response = self.search("meditation")

        self.assertEqual(response.status_code, 200)
        facility = response.json()["facilities"][0]
        self.assertEqual(facility["name"], "Sunset Yoga Studio")
        self.assertEqual(
            facility["description"],
            "Small-group yoga and meditation classes.",
        )
        self.assertEqual(facility["category"], "Fitness")
        self.assertEqual(facility["price"], 280000)
        self.assertEqual(
            facility["picture"],
            "https://picsum.photos/seed/yoga-test/800/600",
        )
        self.assertEqual(facility["rating"], 4.7)
        self.assertFalse(facility["availability"])

    def test_searches_description_and_category(self):
        Facility.objects.create(
            name="Northside Arena",
            description="Hosts weekly volleyball tournaments.",
            category="Volleyball",
            type="Sports Hall",
            location="North Park",
        )

        self.assertEqual(self.names(self.search("tournaments")), ["Northside Arena"])
        self.assertEqual(self.names(self.search("volleyball")), ["Northside Arena"])
