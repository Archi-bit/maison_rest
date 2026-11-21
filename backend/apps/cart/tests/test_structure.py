from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.cart.views import cart_item_detail, cart_items, guest_cart


class CartStructureTest(SimpleTestCase):
    def test_cart_route(self):
        for name, kwargs, url, view in (
            ("guest-cart", {}, "/api/v1/cart/", guest_cart),
            ("cart-items", {}, "/api/v1/cart/items/", cart_items),
            (
                "cart-item-detail", {"item_id": 7},
                "/api/v1/cart/items/7/", cart_item_detail,
            ),
        ):
            with self.subTest(name=name):
                self.assertEqual(reverse(name, kwargs=kwargs), url)
                match = resolve(url)
                self.assertEqual(match.func, view)
                self.assertEqual(match.kwargs, kwargs)
