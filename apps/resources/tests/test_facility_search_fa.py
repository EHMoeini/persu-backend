from rest_framework.test import APITestCase

from apps.resources.models import Facility


class PersianFacilitySearchTests(APITestCase):
    def setUp(self):
        self.football = Facility.objects.create(
            name="زمین فوتبال شماره یک",
            type="فوتبال",
            location="مجموعه ورزشی شمال",
        )
        self.turf = Facility.objects.create(
            name="چمن مصنوعی شماره دو",
            type="چمن مصنوعی",
            location="باشگاه غرب",
        )
        self.pool = Facility.objects.create(
            name="استخر سرپوشیده",
            type="استخر",
            location="مجموعه ورزشی مرکز",
        )
        self.tennis = Facility.objects.create(
            name="زمین تنیس",
            type="تنیس",
            location="باشگاه شرق",
        )
        self.badminton = Facility.objects.create(
            name="زمین بدمینتون",
            type="بدمینتون",
            location="سالن ورزشی جنوب",
        )
        self.sports_hall = Facility.objects.create(
            name="سالن ورزشی چندمنظوره",
            type="سالن ورزشی",
            location="مرکز شهر",
        )
        self.futsal = Facility.objects.create(
            name="زمین فوتسال",
            type="فوتسال",
            location="مجموعه ورزشی شمال",
        )

    def search(self, query: str | None = None):
        params = {} if query is None else {"q": query}
        return self.client.get("/api/facilities", params)

    def names(self, response) -> list[str]:
        return [item["name"] for item in response.json()["facilities"]]

    def test_full_persian_football_query_returns_related_listings(self):
        response = self.search("زمین فوتبال")

        self.assertEqual(response.status_code, 200)
        names = self.names(response)
        self.assertTrue(names[0].startswith("زمین فوتبال"))
        self.assertIn("چمن مصنوعی شماره دو", names)
        self.assertNotIn("زمین تنیس", names)
        self.assertNotIn("استخر سرپوشیده", names)

    def test_football_finds_pitch_and_artificial_turf(self):
        response = self.search("فوتبال")

        self.assertEqual(response.status_code, 200)
        names = self.names(response)
        self.assertTrue(names[0].startswith("زمین فوتبال"))
        self.assertIn("چمن مصنوعی شماره دو", names)
        self.assertNotIn("زمین تنیس", names)
        self.assertNotIn("استخر سرپوشیده", names)

    def test_swimming_query_finds_pool(self):
        response = self.search("شنا")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response)[0], "استخر سرپوشیده")
        self.assertNotIn("زمین تنیس", self.names(response))

    def test_pool_query_finds_pool(self):
        response = self.search("استخر")

        self.assertEqual(self.names(response), ["استخر سرپوشیده"])

    def test_tennis_query_returns_only_tennis(self):
        response = self.search("تنیس")

        self.assertEqual(self.names(response), ["زمین تنیس"])

    def test_tennis_phrase_query_returns_only_tennis(self):
        response = self.search("زمین تنیس")

        self.assertEqual(self.names(response), ["زمین تنیس"])

    def test_badminton_queries_return_badminton(self):
        for query in ("بدمینتون", "زمین بدمینتون"):
            response = self.search(query)

            self.assertIn("زمین بدمینتون", self.names(response))
            self.assertNotIn("استخر سرپوشیده", self.names(response))

    def test_artificial_turf_query(self):
        response = self.search("چمن مصنوعی")

        self.assertEqual(self.names(response), ["چمن مصنوعی شماره دو"])

    def test_sports_hall_query_prefers_hall(self):
        response = self.search("سالن ورزشی")

        names = self.names(response)
        self.assertEqual(names[0], "سالن ورزشی چندمنظوره")
        self.assertIn("زمین بدمینتون", names)

    def test_futsal_query_returns_futsal(self):
        response = self.search("فوتسال")

        names = self.names(response)
        self.assertEqual(names[0], "زمین فوتسال")
        self.assertIn("زمین فوتبال شماره یک", names)

    def test_partial_persian_queries(self):
        cases = {
            "فوت": {"زمین فوتبال شماره یک", "زمین فوتسال"},
            "استخ": {"استخر سرپوشیده"},
            "تنی": {"زمین تنیس"},
            "بدمین": {"زمین بدمینتون"},
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(set(self.names(self.search(query))), expected)

    def test_persian_arabic_character_variants(self):
        Facility.objects.create(
            name="زمین تنيـس",
            type="تنیس",
            location="باشگاه",
        )
        Facility.objects.create(
            name="سالن كشتي",
            type="کشتی",
            location="باشگاه",
        )

        tennis_names = self.names(self.search("تنیس"))
        self.assertIn("زمین تنيـس", tennis_names)
        self.assertIn("زمین تنیس", tennis_names)

        for query in ("کشتی", "كشتي"):
            self.assertIn("سالن كشتي", self.names(self.search(query)))

    def test_extra_spaces_and_zwnj_are_normalized(self):
        for query in ("  زمین   فوتبال  ", "زمین\u200cفوتبال"):
            response = self.search(query)

            self.assertEqual(response.status_code, 200)
            self.assertTrue(self.names(response)[0].startswith("زمین فوتبال"))

        for query in ("  سالن   ورزشی  ", "سالن\u200cورزشی"):
            response = self.search(query)

            self.assertEqual(self.names(response)[0], "سالن ورزشی چندمنظوره")

    def test_minor_spelling_variations_are_tolerated(self):
        self.assertIn("زمین فوتبال شماره یک", self.names(self.search("فتبال")))
        self.assertIn("زمین بدمینتون", self.names(self.search("بدمینتن")))

    def test_arbitrary_terms_use_the_general_matching_algorithm(self):
        Facility.objects.create(
            name="زمین والیبال",
            type="والیبال",
            location="مجموعه ورزشی",
        )

        self.assertIn("زمین والیبال", self.names(self.search("والیبال")))
        self.assertIn("زمین والیبال", self.names(self.search("والیب")))

    def test_english_queries_match_persian_and_english_listings(self):
        Facility.objects.create(
            name="Olympic Swimming Pool",
            type="Swimming Pool",
            location="Downtown",
        )

        swimming = self.names(self.search("swimming"))
        self.assertEqual(swimming[0], "Olympic Swimming Pool")
        self.assertIn("استخر سرپوشیده", swimming)

        self.assertIn("زمین تنیس", self.names(self.search("tennis")))

        soccer = self.names(self.search("soccer"))
        self.assertIn("زمین فوتبال شماره یک", soccer)
        self.assertIn("چمن مصنوعی شماره دو", soccer)

        self.assertIn("Olympic Swimming Pool", self.names(self.search("POOL")))

    def test_empty_query_returns_all_facilities(self):
        for query in (None, "", "   "):
            response = self.search(query)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["facilities"]), 7)
