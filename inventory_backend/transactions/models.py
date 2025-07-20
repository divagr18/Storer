from django.db import models
from suppliers.models import Supplier


class Transaction(models.Model):
    TRANSACTION_TYPES = [("sale", "Sale"), ("purchase", "Purchase")]
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    transaction_date = models.DateTimeField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0
    )
    customer_name = models.CharField(max_length=100, blank=True, null=True, default="")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, blank=True, null=True, default=None
    )
    transaction_id = models.CharField(
        max_length=50, unique=True, blank=True, null=True, default=""
    )
    weather_condition = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Weather condition on transaction date",
    )
    is_holiday = models.BooleanField(
        default=False, help_text="Is the transaction date a holiday?"
    )
    is_promotion = models.BooleanField(
        default=False, help_text="Was there a promotion on the transaction date?"
    )

    def __str__(self):
        """Return a string representation of the transaction.

        The string includes the transaction type and the associated product's name.

        Returns:
            str: A formatted string in the form "<transaction_type> - <product_name>"."""
        return f"{self.transaction_type} - {self.product.name}"

    class Meta:
        db_table = "transactions"

    def save(self, *args, **kwargs):
        """Calculates the total amount as unit_price multiplied by quantity and saves the model instance.

        Overrides the default save method to ensure total_amount is updated before persisting the instance.

        Args:
            *args: Variable length argument list to pass to the superclass save method.
            **kwargs: Arbitrary keyword arguments to pass to the superclass save method.

        Returns:
            None"""
        self.total_amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)
