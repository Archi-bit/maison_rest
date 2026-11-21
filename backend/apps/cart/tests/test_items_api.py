from decimal import Decimal
from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.cart.services import MAX_ITEM_QUANTITY, create_guest_cart
from apps.catalog.models import Dish


class CartItemsAPITest(TestCase):
    client_class = APIClient

    @classmethod
    def setUpTestData(cls):
        cls.cart = create_guest_cart()
        cls.other_cart = create_guest_cart()
        cls.dish = Dish.objects.create(name="Суп", price=Decimal("125.10"))
        cls.dessert = Dish.objects.create(
            name="Десерт", price=Decimal("90.25")
        )

    def setUp(self):
        self.url = reverse("cart-items")
        self.client.credentials(HTTP_X_CART_TOKEN=str(self.cart.token))

    def item_url(self, item_id):
        return reverse("cart-item-detail", args=[item_id])

    def test_adds_new_dish(self):
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        item = CartItem.objects.get(cart=self.cart)
        self.assertEqual(
            response.json(),
            {"id": item.pk, "dish_id": self.dish.pk, "quantity": 2},
        )
        self.assertEqual(response["X-Cart-Token"], str(self.cart.token))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.cart.refresh_from_db()
        self.assertGreater(self.cart.updated_at, self.cart.created_at)

    def test_adding_same_dish_increases_quantity(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=2
        )
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], item.pk)
        self.assertEqual(response.json()["quantity"], 5)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)
        self.assertEqual(self.cart.items.count(), 1)

    def test_adding_dish_does_not_change_other_cart(self):
        other_item = CartItem.objects.create(
            cart=self.other_cart, dish=self.dish, quantity=5
        )
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.json()["id"], other_item.pk)
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 5)

    def test_rejects_missing_or_invalid_dish(self):
        for dish_id in (None, self.dessert.pk + 100, "invalid", True):
            with self.subTest(dish_id=dish_id):
                response = self.client.post(
                    self.url,
                    {"dish_id": dish_id, "quantity": 1},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("dish_id", response.json())
        response = self.client.post(
            self.url, {"quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dish_id", response.json())
        self.assertFalse(CartItem.objects.exists())

    def test_rejects_fractional_dish_id_without_adding_another_dish(self):
        response = self.client.post(
            self.url,
            {"dish_id": self.dish.pk + 0.5, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dish_id", response.json())
        self.assertFalse(CartItem.objects.exists())

    def test_add_and_patch_reject_invalid_quantities(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=2
        )
        for quantity in (
            0, -1, 1.5, "abc", None, True, [], MAX_ITEM_QUANTITY + 1
        ):
            with self.subTest(quantity=quantity):
                responses = [
                    self.client.post(
                        self.url,
                        {"dish_id": self.dish.pk, "quantity": quantity},
                        format="json",
                    ),
                    self.client.patch(
                        self.item_url(item.pk),
                        {"quantity": quantity},
                        format="json",
                    ),
                ]
                for response in responses:
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("quantity", response.json())
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_quantity_is_required_for_add_and_patch(self):
        item = CartItem.objects.create(cart=self.cart, dish=self.dish)
        responses = [
            self.client.post(
                self.url, {"dish_id": self.dish.pk}, format="json"
            ),
            self.client.patch(self.item_url(item.pk), {}, format="json"),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 400)
            self.assertIn("quantity", response.json())
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_rejects_overflow_when_adding_to_existing_item(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=MAX_ITEM_QUANTITY
        )
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.json())
        item.refresh_from_db()
        self.assertEqual(item.quantity, MAX_ITEM_QUANTITY)
        self.assertEqual(self.cart.items.count(), 1)

    def test_patch_replaces_quantity(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=2
        )
        previous_updated_at = self.cart.updated_at
        response = self.client.patch(
            self.item_url(item.pk), {"quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": item.pk, "dish_id": self.dish.pk, "quantity": 3},
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.cart.refresh_from_db()
        self.assertGreater(self.cart.updated_at, previous_updated_at)

    def test_patch_and_delete_missing_item(self):
        for method in (self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(
                    self.item_url(99999), {"quantity": 1}, format="json"
                )
                self.assertEqual(response.status_code, 404)
                self.assertIn("detail", response.json())

    def test_patch_and_delete_cannot_access_other_cart_item(self):
        other_item = CartItem.objects.create(
            cart=self.other_cart, dish=self.dish, quantity=2
        )
        for method in (self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(
                    self.item_url(other_item.pk),
                    {"quantity": 3},
                    format="json",
                )
                self.assertEqual(response.status_code, 404)
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 2)

    def test_delete_removes_only_requested_item(self):
        item = CartItem.objects.create(cart=self.cart, dish=self.dish)
        dessert_item = CartItem.objects.create(
            cart=self.cart, dish=self.dessert
        )
        other_item = CartItem.objects.create(
            cart=self.other_cart, dish=self.dish
        )
        previous_updated_at = self.cart.updated_at
        response = self.client.delete(self.item_url(item.pk))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["X-Cart-Token"], str(self.cart.token))
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=dessert_item.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=other_item.pk).exists())
        self.assertEqual(Cart.objects.count(), 2)
        self.assertTrue(Dish.objects.filter(pk=self.dish.pk).exists())
        self.cart.refresh_from_db()
        self.assertGreater(self.cart.updated_at, previous_updated_at)
        repeated = self.client.delete(self.item_url(item.pk))
        self.assertEqual(repeated.status_code, 404)

    def test_all_mutations_require_valid_cart_token(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=2
        )
        for token, expected_status in (
            (None, 400), ("", 400), ("invalid", 400), (str(uuid4()), 404)
        ):
            self.client.credentials(
                **({} if token is None else {"HTTP_X_CART_TOKEN": token})
            )
            for method, url, payload in (
                (self.client.post, self.url,
                 {"dish_id": self.dish.pk, "quantity": 3}),
                (self.client.patch, self.item_url(item.pk), {"quantity": 3}),
                (self.client.delete, self.item_url(item.pk), {}),
            ):
                with self.subTest(token=token, method=method.__name__):
                    response = method(url, payload, format="json")
                    self.assertEqual(response.status_code, expected_status)
                    self.assertIn("detail", response.json())
                    self.assertNotIn("X-Cart-Token", response)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(Cart.objects.count(), 2)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_totals_after_add_patch_and_delete(self):
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        item_id = response.json()["id"]
        response = self.client.post(
            self.url,
            {"dish_id": self.dessert.pk, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        cart_url = reverse("guest-cart")
        self.assertEqual(
            self.client.get(cart_url).json(),
            {"total_quantity": 3, "total_price": "340.45"},
        )
        response = self.client.patch(
            self.item_url(item_id), {"quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(cart_url).json(),
            {"total_quantity": 4, "total_price": "465.55"},
        )
        self.assertEqual(
            self.client.delete(self.item_url(item_id)).status_code, 204
        )
        self.assertEqual(
            self.client.get(cart_url).json(),
            {"total_quantity": 1, "total_price": "90.25"},
        )

    def test_totals_use_updated_catalog_price(self):
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        cart_url = reverse("guest-cart")
        self.assertEqual(
            self.client.get(cart_url).json(),
            {"total_quantity": 3, "total_price": "375.30"},
        )

        self.dish.price = Decimal("130.15")
        self.dish.save(update_fields=["price"])

        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"total_quantity": 3, "total_price": "390.45"},
        )

    def test_deleted_dish_is_removed_from_carts_and_cannot_be_added(self):
        response = self.client.post(
            self.url, {"dish_id": self.dish.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        item_id = response.json()["id"]
        response = self.client.post(
            self.url,
            {"dish_id": self.dessert.pk, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        CartItem.objects.create(cart=self.other_cart, dish=self.dish)
        dish_id = self.dish.pk

        self.dish.delete()

        response = self.client.get(reverse("guest-cart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"total_quantity": 1, "total_price": "90.25"},
        )
        self.assertFalse(CartItem.objects.filter(dish_id=dish_id).exists())
        self.assertEqual(Cart.objects.count(), 2)
        for method in (self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(
                    self.item_url(item_id), {"quantity": 1}, format="json"
                )
                self.assertEqual(response.status_code, 404)
        response = self.client.post(
            self.url, {"dish_id": dish_id, "quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dish_id", response.json())
        self.assertEqual(CartItem.objects.count(), 1)

    def test_unsupported_methods_and_options_do_not_change_items(self):
        item = CartItem.objects.create(cart=self.cart, dish=self.dish)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(
            self.client.post(self.item_url(item.pk)).status_code, 405
        )
        self.assertEqual(self.client.options(self.url).status_code, 200)
        self.assertEqual(
            self.client.options(self.item_url(item.pk)).status_code, 200
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)
        self.assertEqual(CartItem.objects.count(), 1)

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_cors_allows_item_operations_and_exposes_cart_token(self):
        item = CartItem.objects.create(cart=self.cart, dish=self.dish)
        for method, url, payload, expected_status in (
            (
                self.client.post, self.url,
                {"dish_id": self.dish.pk, "quantity": 2}, 200,
            ),
            (
                self.client.patch, self.item_url(item.pk),
                {"quantity": 3}, 200,
            ),
            (self.client.delete, self.item_url(item.pk), {}, 204),
        ):
            with self.subTest(method=method.__name__):
                response = method(
                    url, payload, format="json",
                    HTTP_ORIGIN="http://localhost:5173",
                )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(
                    response["Access-Control-Allow-Origin"],
                    "http://localhost:5173",
                )
                self.assertEqual(
                    response["X-Cart-Token"], str(self.cart.token)
                )
                self.assertIn(
                    "x-cart-token",
                    response["Access-Control-Expose-Headers"].lower(),
                )
        self.assertFalse(self.cart.items.exists())
