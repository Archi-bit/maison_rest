from decimal import Decimal
from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.cart.models import Cart, CartItem
from apps.cart.services import create_guest_cart
from apps.catalog.models import Dish


class GuestCartTest(TestCase):
    def setUp(self):
        self.url = reverse("guest-cart")

    def test_post_creates_guest_cart_and_returns_token(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response["X-Cart-Token"], str(Cart.objects.get().token)
        )
        self.assertEqual(
            response.json(), {"total_quantity": 0, "total_price": "0.00"}
        )
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("sessionid", response.cookies)

    def test_valid_token_returns_same_cart_and_totals(self):
        cart = create_guest_cart()
        dish = Dish.objects.create(name="Суп", price=Decimal("125.10"))
        CartItem.objects.create(cart=cart, dish=dish, quantity=3)
        other_cart = create_guest_cart()
        CartItem.objects.create(cart=other_cart, dish=dish, quantity=10)
        for method in (self.client.get, self.client.post):
            with self.subTest(method=method.__name__):
                response = method(self.url, HTTP_X_CART_TOKEN=str(cart.token))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["X-Cart-Token"], str(cart.token))
                self.assertEqual(
                    response.json(),
                    {"total_quantity": 3, "total_price": "375.30"},
                )
        self.assertEqual(Cart.objects.count(), 2)

    def test_get_without_token_does_not_create_cart(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("X-Cart-Token", response.json()["detail"])
        self.assertFalse(Cart.objects.exists())

    def test_invalid_or_unknown_tokens_do_not_create_cart(self):
        cart = create_guest_cart()
        for token, expected_status in (
            ("", 400),
            ("not-a-uuid", 400),
            (str(uuid4()), 404),
        ):
            for method in (self.client.get, self.client.post):
                with self.subTest(token=token, method=method.__name__):
                    response = method(self.url, HTTP_X_CART_TOKEN=token)
                    self.assertEqual(response.status_code, expected_status)
                    self.assertIn("detail", response.json())
                    self.assertNotIn(
                        str(cart.token), response.content.decode()
                    )
                    self.assertNotIn("X-Cart-Token", response)
        self.assertEqual(Cart.objects.count(), 1)

    def test_other_http_methods_do_not_create_cart(self):
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertEqual(method(self.url).status_code, 405)
        self.assertFalse(Cart.objects.exists())

    def test_options_does_not_create_cart(self):
        self.assertEqual(self.client.options(self.url).status_code, 200)
        self.assertFalse(Cart.objects.exists())

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_cors_allows_and_exposes_cart_token(self):
        preflight = self.client.options(
            self.url,
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-cart-token",
        )
        self.assertEqual(preflight.status_code, 200)
        self.assertIn(
            "x-cart-token", preflight["Access-Control-Allow-Headers"]
        )
        self.assertEqual(
            preflight["Access-Control-Allow-Origin"], "http://localhost:5173"
        )
        self.assertFalse(Cart.objects.exists())
        response = self.client.post(
            self.url, HTTP_ORIGIN="http://localhost:5173"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(
            "X-Cart-Token", response["Access-Control-Expose-Headers"]
        )
        token = response["X-Cart-Token"]
        response = self.client.get(
            self.url,
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_X_CART_TOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Cart-Token"], token)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "http://localhost:5173"
        )
        self.assertEqual(Cart.objects.count(), 1)

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_cors_does_not_allow_unknown_origin(self):
        response = self.client.options(
            self.url,
            HTTP_ORIGIN="https://unknown.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertFalse(Cart.objects.exists())
