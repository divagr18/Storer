# products/management/commands/import_kaggle_retail_data.py
from django.core.management.base import BaseCommand
import pandas as pd
from products.models import Product
from transactions.models import Transaction
from inventory_logs.models import InventoryLog  # Import InventoryLog
from django.utils import timezone  # Import timezone for making dates timezone-aware
import uuid


class Command(BaseCommand):
    help = 'Imports product and transaction data from the Kaggle Retail dataset'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the Kaggle CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        try:
            df = pd.read_csv(csv_file_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file_path}"))
            return

        self.stdout.write(self.style.SUCCESS('Importing Kaggle Retail data with Weather/Holiday/Promotion...'))

        processed_products = set()  # Track processed product SKUs to avoid duplicates

        for index, row in df.iterrows():
            sku = f"{row['Category']}-{row['Product ID']}"  # Create composite SKU

            # --- Product Creation/Update ---
            product, product_created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': f"{row['Category']} Product {row['Product ID']}",
                    'description': f"Product in {row['Category']} category, ID {row['Product ID']}",
                    'category': row['Category'],
                    'price': 15.00,  # Default price
                    'unit': 'unit',   # Default unit
                    'cost_price': 7.50  # Default cost price
                }
            )

            if product_created:
                self.stdout.write(self.style.SUCCESS(f"  Created Product: {product.name} (SKU: {product.sku})"))
            elif sku not in processed_products:
                self.stdout.write(self.style.WARNING(f"  Product with SKU: {product.sku} already exists. Skipping product creation."))
                processed_products.add(sku)

            # --- Transaction Creation ---
            transaction_date = pd.to_datetime(row['Date']).to_pydatetime()

            # Assuming 'Holiday/Promotion' column indicates EITHER a Holiday OR a Promotion (or both)
            is_holiday_or_promotion = bool(row['Holiday/Promotion'])

            Transaction.objects.create(
                product=product,
                transaction_type='sale',
                transaction_date=transaction_date,
                quantity=row['Units Sold'],
                unit_price=product.price,
                customer_name='Kaggle Customer',
                transaction_id=uuid.uuid4(),

                # --- Populate new fields with CORRECT column names ---
                weather_condition=row['Weather Condition'],
                is_holiday=is_holiday_or_promotion,  # Use combined flag for both holiday and promotion
                is_promotion=is_holiday_or_promotion # Use combined flag for both holiday and promotion
            )

        self.stdout.write(self.style.SUCCESS('Kaggle Retail data import completed successfully with Weather/Holiday/Promotion!'))