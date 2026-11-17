from django.test import SimpleTestCase
from django.urls import reverse


class HealthTest(SimpleTestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_health_endpoint(self):
        response = self.client.get(
            reverse("api-health"), HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(
            response.json(),
            {"status": "ok", "project": "MAISON Restaurant"},
        )

    def test_api_health_rejects_post(self):
        response = self.client.post(reverse("api-health"))
        self.assertEqual(response.status_code, 405)

    def test_admin_route(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(
            response, "/admin/login/?next=/admin/", fetch_redirect_response=False
        )

    def test_api_login_route(self):
        response = self.client.get(reverse("rest_framework:login"))
        self.assertEqual(response.status_code, 200)
