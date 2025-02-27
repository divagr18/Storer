from django.db import models
from suppliers.models import Supplier
from .utils import calculate_reorder_point

class Product(models.Model):
    name = models.CharField(max_length=100) # No default needed, should always have a name
    description = models.TextField(blank=True, null=True, default="") # Provide an empty string
    price = models.DecimalField(max_digits=10, decimal_places=2) # No default needed, critical for accurate price tracking
    stock_level = models.IntegerField(default=0)
    category = models.CharField(max_length=50, blank=True, null=True, default="") # Provide an empty string
    created_at = models.DateTimeField(auto_now_add=True) # Auto-generated, no default needed
    sku = models.CharField(max_length=50, unique=True) #  NOT NULL
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, help_text="Primary supplier") # Add this

    min_stock_level = models.IntegerField(default=0, null=False) # Changed to null=False
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # set a default of 0
    unit = models.CharField(max_length=20, default="unit")
    reorder_point = models.IntegerField(default=10)
    lead_time_days = models.IntegerField(default=7)  # Provide a reasonable average lead time.
    discontinued = models.BooleanField(default=False)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku: # If SKU is not set, generate one
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)
    def update_reorder_point(self):
        """
        Updates the reorder point for the product.
        """
        self.reorder_point = calculate_reorder_point(self)
        self.save()
    def generate_sku(self):
        """Generates a unique SKU for the product."""
        import uuid
        return str(uuid.uuid4())[:12].upper()  # Generate a random UUID-based SKU (adjust length as needed)

    class Meta:
        db_table = 'products'
