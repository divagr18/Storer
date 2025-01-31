from django.db import models
from products.models import Product

class InventoryLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stock_change = models.IntegerField()  # +ve for additions, -ve for removals
    reason = models.CharField(max_length=255, blank=True, null=True)
    change_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Change: {self.stock_change} for {self.product.name} on {self.change_date}"
    class Meta:
        db_table = 'Inventory_logs'