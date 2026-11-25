from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class SchemaTest(SimpleTestCase):
    def test_schema_describes_cart_operations_and_token(self):
        response = self.client.get(
            "/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("get", paths["/api/v1/health/"])

        for path, method, statuses in (
            ("/api/v1/cart/", "get", ("200",)),
            ("/api/v1/cart/", "post", ("200", "201")),
            ("/api/v1/cart/items/", "post", ("200", "201")),
            ("/api/v1/cart/items/{item_id}/", "patch", ("200",)),
            ("/api/v1/cart/items/{item_id}/", "delete", ("204",)),
        ):
            with self.subTest(path=path, method=method):
                operation = paths[path][method]
                token = next(
                    parameter for parameter in operation["parameters"]
                    if parameter["name"] == "X-Cart-Token"
                )
                self.assertEqual(token["in"], "header")
                creates_cart = path == "/api/v1/cart/" and method == "post"
                self.assertEqual(token.get("required", False), not creates_cart)
                for status in statuses:
                    headers = operation["responses"][status]["headers"]
                    self.assertIn("X-Cart-Token", headers)

    def test_swagger_uses_server_schema_and_local_assets(self):
        response = self.client.get("/api/swagger/")
        self.assertContains(response, "/api/schema/")
        for asset in ("swagger-ui.css", "swagger-ui-bundle.js"):
            with self.subTest(asset=asset):
                path = f"drf_spectacular_sidecar/swagger-ui-dist/{asset}"
                self.assertContains(response, f"/static/{path}")
                self.assertIsNotNone(finders.find(path))
