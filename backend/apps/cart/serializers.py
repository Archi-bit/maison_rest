from rest_framework import serializers

from apps.cart.models import CartItem
from apps.cart.services import MAX_ITEM_QUANTITY
from apps.catalog.models import Dish


class CartSummarySerializer(serializers.Serializer):
    total_quantity = serializers.IntegerField(min_value=0)
    total_price = serializers.CharField(
        help_text="Сумма с двумя знаками после запятой."
    )


class CartItemSerializer(serializers.ModelSerializer):
    dish_id = serializers.PrimaryKeyRelatedField(
        source="dish",
        queryset=Dish.objects.all(),
        pk_field=serializers.IntegerField(min_value=1),
    )
    quantity = serializers.IntegerField(
        min_value=1, max_value=MAX_ITEM_QUANTITY
    )

    class Meta:
        model = CartItem
        fields = ("id", "dish_id", "quantity")
        read_only_fields = ("id",)


class CartItemQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1, max_value=MAX_ITEM_QUANTITY
    )
