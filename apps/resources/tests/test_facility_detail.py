from rest_framework.test import APITestCase

from apps.resources.models import Facility


class FacilityDetailAndFilterTests(APITestCase):
    def setUp(self):
        self.tehran_futsal = Facility.objects.create(
            name="سالن فوتسال ولنجک",
            type="فوتسال",
            location="تهران - ولنجک",
            city="تهران",
            province="تهران",
            district="ولنجک",
            address="تهران، ولنجک، بلوار دانشجو",
            latitude=35.8049,
            longitude=51.3982,
            phone="09040980179",
            price_irr=7000000,
            price_display="700,000 تومان",
            rating=4.5,
            rating_count=12,
            opening_hours="08:00 - 23:00",
            sports=["فوتسال", "والیبال"],
            amenities=["پارکینگ", "بوفه"],
            source_name="asansport",
            external_id="asansport:test1",
        )
        self.mashhad_pool = Facility.objects.create(
            name="استخر موج‌های آبی",
            type="استخر",
            location="مشهد - قاسم‌آباد",
            city="مشهد",
            province="خراسان رضوی",
            source_name="poolticket",
            external_id="poolticket:test2",
        )

    def test_filter_by_city_and_type(self):
        res = self.client.get("/api/facilities", {"city": "تهران", "type": "فوتسال"})
        self.assertEqual(res.status_code, 200)
        facilities = res.json()["facilities"]
        self.assertEqual(len(facilities), 1)
        self.assertEqual(facilities[0]["name"], "سالن فوتسال ولنجک")

    def test_detail_endpoint_returns_enriched_fields(self):
        res = self.client.get(f"/api/facilities/{self.tehran_futsal.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["city"], "تهران")
        self.assertEqual(data["price_irr"], 7000000)
        self.assertEqual(data["sports"], ["فوتسال", "والیبال"])
        self.assertEqual(data["amenities"], ["پارکینگ", "بوفه"])
        self.assertAlmostEqual(data["latitude"], 35.8049, places=3)
