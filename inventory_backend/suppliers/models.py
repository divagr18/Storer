from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=100) # No default. All suppliers should have a name.
    contact_name = models.CharField(max_length=100, blank=True, null=True, default="") # Provide an empty string
    contact_email = models.EmailField(blank=True, null=True, default="")  # Provide an empty string
    phone_number = models.CharField(max_length=15, blank=True, null=True, default="") # Provide an empty string
    address = models.TextField(blank=True, null=True, default="") # Provide an empty string
    created_at = models.DateTimeField(auto_now_add=True) # Auto-generated, no default needed
    supplier_code = models.CharField(max_length=50, unique=True, blank=True, null=True, default="")
    payment_terms = models.CharField(max_length=100, blank=True, null=True, default="")
    notes = models.TextField(blank=True, null=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'suppliers'