from django.db import models
from products.models import Product
from suppliers.models import Supplier # Import supplier model

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
    ]

    product = models.ForeignKey('products.Product', on_delete=models.CASCADE) # No default
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES) # No default
    quantity = models.IntegerField() # No default
    transaction_date = models.DateTimeField() # No default

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Set a default of 0
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0.00) # Provide a default
    customer_name = models.CharField(max_length=100, blank=True, null=True, default="") # provide a default
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True, default=None)
    transaction_id = models.CharField(max_length=50, unique=True, blank=True, null=True, default="")

    weather_condition = models.CharField(max_length=50, blank=True, null=True, help_text="Weather condition on transaction date")
    is_holiday = models.BooleanField(default=False, help_text="Is the transaction date a holiday?")
    is_promotion = models.BooleanField(default=False, help_text="Was there a promotion on the transaction date?")

    def __str__(self):
        return f"{self.transaction_type} - {self.product.name}"

    class Meta:
        db_table = 'transactions'

    def save(self, *args, **kwargs):
        # Calculate total_amount before saving
        self.total_amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)