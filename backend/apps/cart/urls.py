from django.urls import path

from apps.cart.views import cart_item_detail, cart_items, guest_cart


urlpatterns = [
    path("cart/", guest_cart, name="guest-cart"),
    path("cart/items/", cart_items, name="cart-items"),
    path(
        "cart/items/<int:item_id>/", cart_item_detail, name="cart-item-detail"
    ),
]
