from django.db import models
from suppliers.models import Supplier
from .utils import calculate_reorder_point


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_level = models.IntegerField(default=0)
    category = models.CharField(max_length=50, blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    sku = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary supplier",
    )
    min_stock_level = models.IntegerField(default=0, null=False)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    unit = models.CharField(max_length=20, default="unit")
    reorder_point = models.IntegerField(default=10)
    lead_time_days = models.IntegerField(default=7)
    discontinued = models.BooleanField(default=False)
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)

    def __str__(self):
        """Returns the product's name as its string representation.

        This method is called to provide a human-readable string for instances of the product model,
        typically used in administrative interfaces and logging.

        Returns:
            str: The name of the product."""
        return self.name

    def save(self, *args, **kwargs):
        """Saves the product instance, generating and assigning a SKU if it is not already set.

        Args:
            *args: Variable length argument list passed to the parent save method.
            **kwargs: Arbitrary keyword arguments passed to the parent save method.

        Returns:
            None

        This method overrides the default save behavior to ensure that each product has a SKU before saving to the database."""
        if not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    def update_reorder_point(self):
        """Updates the product's reorder point by recalculating it and saving the updated value.

        This method recalculates the reorder point based on current product data using the
        `calculate_reorder_point` function, then persists the change to the database.

        Args:
            None

        Returns:
            None"""
        self.reorder_point = calculate_reorder_point(self)
        self.save()

    def generate_sku(self):
        """Generates a unique SKU string for the product using a UUID.

        The SKU is created by generating a UUID4, converting it to a string,
        taking the first 12 characters, and converting them to uppercase.

        Returns:
            str: A 12-character uppercase string serving as a unique SKU."""
        import uuid

        return str(uuid.uuid4())[:12].upper()

    class Meta:
        db_table = "products"
