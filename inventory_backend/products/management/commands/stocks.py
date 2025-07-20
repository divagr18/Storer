from django.core.management.base import BaseCommand
from products.models import Product
from transactions.models import Transaction
from django.db.models import Sum
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = "Calculates and updates initial stock levels for products based on transaction data"

    def handle(self, *args, **options):
        """Calculates and updates the stock levels for all products based on purchase and sale transactions.

        Iterates over all Product instances, computes the total purchased and sold quantities from related Transaction records,
        and updates each product's stock_level accordingly.

        Args:
            *args: Variable length argument list (not used).
            **options: Arbitrary keyword arguments (not used).

        Returns:
            None

        Outputs progress and completion messages to standard output, indicating the update status for each product."""
        self.stdout.write(
            self.style.SUCCESS("Calculating and updating stock levels...")
        )
        for product in Product.objects.all():
            stock_level = 0
            total_purchased = (
                Transaction.objects.filter(
                    product=product, transaction_type="purchase"
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )
            total_purchased = total_purchased if total_purchased is not None else 0
            total_sold = (
                Transaction.objects.filter(
                    product=product, transaction_type="sale"
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )
            total_sold = total_sold if total_sold is not None else 0
            stock_level = total_purchased - total_sold
            product.stock_level = stock_level
            product.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated stock level for product {product.sku} to {product.stock_level}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Stock level calculation and update completed successfully!"
            )
        )
