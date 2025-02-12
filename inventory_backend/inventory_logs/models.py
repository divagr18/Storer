from django.db import models
from products.models import Product
from django.contrib.auth import get_user_model

class InventoryLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE) # No default, must be associated with product
    stock_change = models.IntegerField()  # No default, represents inventory change
    reason = models.CharField(max_length=255, blank=True, null=True, default="")  # Provide an empty string
    change_date = models.DateTimeField(auto_now_add=True)  # Auto-generated, no default needed
    source = models.CharField(max_length=255, blank=True, null=True, default="")  # Provide an empty string

    User = get_user_model()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, default=None)  # Set the FK default to None

    def __str__(self):
        return f"Change: {self.stock_change} for {self.product.name} on {self.change_date}"

    class Meta:
        db_table = 'Inventory_logs'