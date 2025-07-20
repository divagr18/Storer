from django.core.management.base import BaseCommand
import pandas as pd
from products.models import Product
from transactions.models import Transaction
from inventory_logs.models import InventoryLog
from django.utils import timezone
import uuid


class Command(BaseCommand):
    help = "Imports product and transaction data from the Kaggle Retail dataset"

    def add_arguments(self, parser):
        """Adds a command-line argument to specify the path to the Kaggle CSV file.

        Args:
            parser (argparse.ArgumentParser): The argument parser instance to which the CSV file path argument is added.

        Returns:
            None"""
        parser.add_argument("csv_file", type=str, help="Path to the Kaggle CSV file")

    def handle(self, *args, **options):
        """Loads product and transaction data from a specified Kaggle retail CSV file, creating or updating Product records and generating associated Transaction entries including weather and holiday/promotion info.

        Args:
            *args: Additional positional arguments (unused).
            **options: Command options containing:
                csv_file (str): Path to the CSV file with retail data.

        Returns:
            None

        This management command reads the CSV at `csv_file`, creates products uniquely identified by a composite SKU of category and product ID if they do not exist, and records sales transactions with enriched contextual data such as weather conditions and combined holiday/promotion flags. Outputs progress and error messages to standard output."""
        csv_file_path = options["csv_file"]
        try:
            df = pd.read_csv(csv_file_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file_path}"))
            return
        self.stdout.write(
            self.style.SUCCESS(
                "Importing Kaggle Retail data with Weather/Holiday/Promotion..."
            )
        )
        processed_products = set()
        for index, row in df.iterrows():
            sku = f"{row['Category']}-{row['Product ID']}"
            product, product_created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": f"{row['Category']} Product {row['Product ID']}",
                    "description": f"Product in {row['Category']} category, ID {row['Product ID']}",
                    "category": row["Category"],
                    "price": 15.0,
                    "unit": "unit",
                    "cost_price": 7.5,
                },
            )
            if product_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created Product: {product.name} (SKU: {product.sku})"
                    )
                )
            elif sku not in processed_products:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Product with SKU: {product.sku} already exists. Skipping product creation."
                    )
                )
                processed_products.add(sku)
            transaction_date = pd.to_datetime(row["Date"]).to_pydatetime()
            is_holiday_or_promotion = bool(row["Holiday/Promotion"])
            Transaction.objects.create(
                product=product,
                transaction_type="sale",
                transaction_date=transaction_date,
                quantity=row["Units Sold"],
                unit_price=product.price,
                customer_name="Kaggle Customer",
                transaction_id=uuid.uuid4(),
                weather_condition=row["Weather Condition"],
                is_holiday=is_holiday_or_promotion,
                is_promotion=is_holiday_or_promotion,
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Kaggle Retail data import completed successfully with Weather/Holiday/Promotion!"
            )
        )
