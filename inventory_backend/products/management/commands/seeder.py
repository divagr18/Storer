from django.core.management.base import BaseCommand
from faker import Faker
from products.models import Product
from inventory_logs.models import InventoryLog
from suppliers.models import Supplier
from transactions.models import Transaction
from django.contrib.auth import get_user_model
from django.db import models, transaction as db_transaction
from decimal import Decimal


class Command(BaseCommand):
    help = "Seeds the database with initial data"

    def handle(self, *args, **options):
        """Seeds the database with initial data including users, suppliers, products, transactions, and inventory logs.

        This management command creates default admin and employee users if they do not exist, generates sample suppliers and products with randomized but realistic data using Faker, then simulates inventory transactions (sales and purchases) wrapped in an atomic database transaction. It also updates product stock levels and creates corresponding inventory log entries.

        Args:
            *args: Positional arguments passed to the command (unused).
            **options: Keyword options passed to the command (unused).

        Returns:
            None. Outputs status messages to stdout indicating progress and success."""
        fake = Faker()
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Seeding the database..."))
        try:
            admin_user = User.objects.get(username="admin")
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username="admin", password="password", email="admin@example.com"
            )
        try:
            employee_user = User.objects.get(username="employee1")
        except User.DoesNotExist:
            employee_user = User.objects.create_user(
                username="employee1", password="password", email="employee1@example.com"
            )
        suppliers = []
        for _ in range(5):
            supplier = Supplier.objects.create(
                name=fake.company(),
                contact_name=fake.name(),
                contact_email=fake.email(),
                phone_number=fake.numerify(text="##########"),
                address=fake.address(),
                supplier_code=fake.unique.lexify(text="SUP-????"),
                payment_terms=fake.random_element(
                    elements=["Net 30", "Net 60", "Due on Receipt"]
                ),
                notes=fake.sentence(),
            )
            suppliers.append(supplier)

        def generate_decimal():
            return Decimal(
                str(fake.random_number(digits=3))
                + "."
                + str(fake.random_number(digits=2))
            )

        products = []
        for _ in range(20):
            product = Product.objects.create(
                name=fake.word().capitalize() + " " + fake.word().capitalize(),
                description=fake.sentence(),
                price=generate_decimal(),
                stock_level=fake.random_int(min=0, max=100),
                category=fake.random_element(
                    elements=("Electronics", "Clothing", "Food", "Home Goods")
                ),
                sku=Product.generate_sku(Product),
                cost_price=generate_decimal(),
                unit=fake.random_element(elements=("piece", "kg", "liter", "box")),
                reorder_point=fake.random_int(min=5, max=20),
                lead_time_days=fake.random_int(min=1, max=14),
                discontinued=fake.boolean(),
            )
            products.append(product)
        with db_transaction.atomic():
            for _ in range(50):
                product = fake.random_element(elements=products)
                transaction_type = fake.random_element(elements=("sale", "purchase"))
                quantity = fake.random_int(min=1, max=10)
                unit_price = product.price
                if transaction_type == "sale":
                    customer_name = fake.name()
                    supplier = None
                    stock_change = -quantity
                else:
                    customer_name = None
                    supplier = fake.random_element(elements=suppliers)
                    stock_change = quantity
                transaction_id = fake.unique.lexify(text="TXN-????")
                transaction = Transaction.objects.create(
                    product=product,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    customer_name=customer_name,
                    supplier=supplier,
                    total_amount=unit_price * quantity,
                    transaction_id=transaction_id,
                )
                InventoryLog.objects.create(
                    product=product,
                    stock_change=stock_change,
                    reason=f"{transaction_type.capitalize()} Transaction",
                    source=transaction.transaction_id,
                    user=fake.random_element(elements=[admin_user, employee_user])
                    if User.objects.count() > 0
                    else None,
                )
                Product.objects.filter(pk=product.pk).update(
                    stock_level=models.F("stock_level") + stock_change
                )
        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
