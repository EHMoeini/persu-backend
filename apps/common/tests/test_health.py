from rest_framework.test import APITestCase


class HealthEndpointTests(APITestCase):
    def test_health_is_public_and_reports_ok(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_rejects_non_get_methods(self):
        response = self.client.post("/healthz")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"]["code"], "method_not_allowed")
