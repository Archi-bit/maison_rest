from django.test import SimpleTestCase, override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
class CorsTest(SimpleTestCase):
    def test_preflight_allows_cart_methods_and_headers(self):
        for url, method in (
            ("/api/v1/cart/", "GET"),
            ("/api/v1/cart/", "POST"),
            ("/api/v1/cart/", "OPTIONS"),
            ("/api/v1/cart/items/", "POST"),
            ("/api/v1/cart/items/1/", "PATCH"),
            ("/api/v1/cart/items/1/", "DELETE"),
        ):
            with self.subTest(url=url, method=method):
                response = self.client.options(
                    url,
                    HTTP_ORIGIN="http://localhost:5173",
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
                    HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                        "content-type, x-cart-token"
                    ),
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response["Access-Control-Allow-Origin"],
                    "http://localhost:5173",
                )
                self.assertIn(
                    method,
                    response["Access-Control-Allow-Methods"].split(", "),
                )
                allowed_headers = response[
                    "Access-Control-Allow-Headers"
                ].lower().split(", ")
                self.assertIn("content-type", allowed_headers)
                self.assertIn("x-cart-token", allowed_headers)

    def test_unknown_origins_receive_no_cors_permission(self):
        for origin in (
            "https://unknown.example",
            "http://localhost:5174",
            "https://localhost:5173",
            "http://localhost:5173.evil.example",
            "null",
        ):
            for method, expected_status in (
                (self.client.get, 400), (self.client.options, 200),
            ):
                with self.subTest(origin=origin, method=method.__name__):
                    response = method(
                        "/api/v1/cart/",
                        HTTP_ORIGIN=origin,
                        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-cart-token",
                    )
                    self.assertEqual(response.status_code, expected_status)
                    self.assertNotIn("Access-Control-Allow-Origin", response)
                    self.assertNotIn("Access-Control-Expose-Headers", response)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_empty_origin_list_does_not_allow_local_frontend(self):
        response = self.client.options(
            "/api/v1/cart/",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_validation_errors_are_readable_by_allowed_frontend(self):
        response = self.client.get(
            "/api/v1/cart/", HTTP_ORIGIN="http://localhost:5173"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "http://localhost:5173"
        )
        self.assertIn("X-Cart-Token", response.json()["detail"])
