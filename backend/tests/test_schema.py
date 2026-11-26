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

    def test_schema_describes_staff_tokens_and_protected_profile(self):
        response = self.client.get(
            "/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        paths = schema["paths"]
        components = schema["components"]
        schemas = components["schemas"]
        self.assertEqual(
            components["securitySchemes"]["jwtAuth"],
            {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        )

        for path, request_fields, response_fields in (
            ("login", {"username", "password"}, {"access", "refresh"}),
            ("token/refresh", {"refresh"}, {"access"}),
        ):
            with self.subTest(path=path):
                operation = paths[f"/api/v1/staff/{path}/"]["post"]
                self.assertFalse(operation.get("security"))
                request_ref = operation["requestBody"]["content"][
                    "application/json"
                ]["schema"]["$ref"]
                response_ref = operation["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]["$ref"]
                request_schema = schemas[request_ref.rsplit("/", 1)[-1]]
                response_schema = schemas[response_ref.rsplit("/", 1)[-1]]
                self.assertEqual(
                    set(request_schema["properties"]), request_fields
                )
                self.assertEqual(
                    set(response_schema["properties"]), response_fields
                )

        profile = paths["/api/v1/staff/me/"]["get"]
        self.assertEqual(profile["security"], [{"jwtAuth": []}])
        profile_ref = profile["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        self.assertEqual(
            set(schemas[profile_ref.rsplit("/", 1)[-1]]["properties"]),
            {"id", "first_name", "last_name", "username", "role"},
        )

    def test_swagger_uses_server_schema_and_local_assets(self):
        response = self.client.get("/api/swagger/")
        self.assertContains(response, "/api/schema/")
        for asset in ("swagger-ui.css", "swagger-ui-bundle.js"):
            with self.subTest(asset=asset):
                path = f"drf_spectacular_sidecar/swagger-ui-dist/{asset}"
                self.assertContains(response, f"/static/{path}")
                self.assertIsNotNone(finders.find(path))
