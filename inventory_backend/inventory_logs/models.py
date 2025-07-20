from django.db import models
from products.models import Product
from django.contrib.auth import get_user_model


class InventoryLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stock_change = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, null=True, default="")
    change_date = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=255, blank=True, null=True, default="")
    User = get_user_model()
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, default=None
    )

    def __str__(self):
        """Return a human-readable string representation of the inventory log entry.

        The string includes the stock change amount, the associated product's name, and the date of the change.
        This is useful for displaying concise information about inventory adjustments in logs or admin interfaces.

        Returns:
            str: Formatted string describing the inventory change record."""
        return (
            f"Change: {self.stock_change} for {self.product.name} on {self.change_date}"
        )

    class Meta:
        db_table = "Inventory_logs"
