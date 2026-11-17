from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models



class Dish(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="catalog_dish_price_nonnegative",
            ),
        ]

    def __str__(self):
        return self.name
