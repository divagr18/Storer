from django.core.management.base import BaseCommand
from products.models import Product


class Command(BaseCommand):
    help = "Updates the reorder points for all products."

    def handle(self, *args, **options):
        """Handles the update of reorder points for all products in the inventory.

        Retrieves all Product instances and calls their `update_reorder_point` method to refresh reorder levels.
        For each product, a success message is output to the console indicating the updated reorder point.
        Finally, a summary success message is printed after all products have been processed.

        Args:
            *args: Variable length argument list (not used).
            **options: Arbitrary keyword arguments (not used).

        Returns:
            None"""
        products = Product.objects.all()
        for product in products:
            product.update_reorder_point()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated reorder point for {product.name} to {product.reorder_point}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS("Successfully updated reorder points for all products.")
        )
