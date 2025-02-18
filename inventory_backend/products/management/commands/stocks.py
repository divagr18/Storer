# products/management/commands/calculate_stock_levels.py
from django.core.management.base import BaseCommand
from products.models import Product
from transactions.models import Transaction
from django.db.models import Sum
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Calculates and updates initial stock levels for products based on transaction data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Calculating and updating stock levels...'))

        for product in Product.objects.all():
            # Initialize the default stock level if no product is found
            stock_level = 0

            # Calculate total purchased quantity
            total_purchased = Transaction.objects.filter(
                product=product, transaction_type='purchase').aggregate(total=Sum('quantity'))['total'] or 0
            # Sum all purchased values if they exists or set to 0 if none was found
            total_purchased = total_purchased if total_purchased is not None else 0
            
            # Calculate total sold quantity
            total_sold = Transaction.objects.filter(
                product=product, transaction_type='sale').aggregate(total=Sum('quantity'))['total'] or 0
            # Set the value of the sold transactions to 0 if no values were found
            total_sold = total_sold if total_sold is not None else 0

            # Calculate the product's current stock level
            stock_level = total_purchased - total_sold

            product.stock_level = stock_level #Set the value for products to the new stock level
            product.save()

            self.stdout.write(self.style.SUCCESS(
                f'Updated stock level for product {product.sku} to {product.stock_level}'
            ))

        self.stdout.write(self.style.SUCCESS('Stock level calculation and update completed successfully!'))