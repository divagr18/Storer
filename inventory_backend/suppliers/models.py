from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100, blank=True, null=True, default="")
    contact_email = models.EmailField(blank=True, null=True, default="")
    phone_number = models.CharField(max_length=15, blank=True, null=True, default="")
    address = models.TextField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    supplier_code = models.CharField(
        max_length=50, unique=True, blank=True, null=True, default=""
    )
    payment_terms = models.CharField(max_length=100, blank=True, null=True, default="")
    notes = models.TextField(blank=True, null=True, default="")

    def __str__(self):
        """Returns the name of the supplier as its string representation.

        This method is used to provide a human-readable representation of the supplier object,
        typically for display in the Django admin interface or when printed.

        Returns:
            str: The name of the supplier."""
        return self.name

    class Meta:
        db_table = "suppliers"
