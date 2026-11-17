from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.cart.models import CartItem
from apps.cart.services import add_cart_item, create_guest_cart
from apps.catalog.models import Dish


class CartConcurrencyTest(TransactionTestCase):
    def test_concurrent_additions_preserve_quantity_and_unique_item(self):
        cart = create_guest_cart()
        dish = Dish.objects.create(name="Суп", price=Decimal("125.10"))

        for initial_quantity in (0, 1):
            with self.subTest(initial_quantity=initial_quantity):
                CartItem.objects.all().delete()
                if initial_quantity:
                    CartItem.objects.create(
                        cart=cart, dish=dish, quantity=initial_quantity
                    )
                barrier = Barrier(2)

                def add_quantity(quantity):
                    close_old_connections()
                    try:
                        barrier.wait(timeout=10)
                        add_cart_item(cart, dish, quantity)
                    finally:
                        connection.close()

                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(add_quantity, quantity)
                        for quantity in (2, 3)
                    ]
                    for future in futures:
                        future.result(timeout=10)
                item = CartItem.objects.get(cart=cart, dish=dish)
                self.assertEqual(item.quantity, initial_quantity + 5)
