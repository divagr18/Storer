from django.core.management.base import BaseCommand
from faker import Faker
from products.models import Product
from inventory_logs.models import InventoryLog
from suppliers.models import Supplier
from transactions.models import Transaction
from django.contrib.auth import get_user_model
from django.db import models, transaction as db_transaction  # Import for atomic transactions and models
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **options):
        fake = Faker()
        User = get_user_model()  # Get the User model

        self.stdout.write(self.style.SUCCESS('Seeding the database...'))

        # Create some Users (if they don't exist already)
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')

        try:
            employee_user = User.objects.get(username='employee1')
        except User.DoesNotExist:
            employee_user = User.objects.create_user(username='employee1', password='password', email='employee1@example.com')

        # Create Suppliers
        suppliers = []
        for _ in range(5):
            supplier = Supplier.objects.create(
                name=fake.company(),
                contact_name=fake.name(),
                contact_email=fake.email(),
                phone_number=fake.numerify(text='##########'),  # Generate a 10-digit number
                address=fake.address(),
                supplier_code=fake.unique.lexify(text='SUP-????'),
                payment_terms=fake.random_element(elements=['Net 30', 'Net 60', 'Due on Receipt']),  # Add payment terms
                notes=fake.sentence()
            )
            suppliers.append(supplier)

        def generate_decimal():
          return Decimal(str(fake.random_number(digits=3)) + "." + str(fake.random_number(digits=2)))

        # Create Products
        products = []
        for _ in range(20):
            product = Product.objects.create(
                name=fake.word().capitalize() + " " + fake.word().capitalize(),
                description=fake.sentence(),
                price=generate_decimal(),
                stock_level=fake.random_int(min=0, max=100),
                category=fake.random_element(elements=('Electronics', 'Clothing', 'Food', 'Home Goods')),
                sku=Product.generate_sku(Product), # Generate using the method
                cost_price=generate_decimal(),
                unit=fake.random_element(elements=('piece', 'kg', 'liter', 'box')),
                reorder_point=fake.random_int(min=5, max=20),
                lead_time_days=fake.random_int(min=1, max=14),
                discontinued=fake.boolean()  # Randomly discontinue some products
            )
            products.append(product)

        # Create Transactions and Inventory Logs
        with db_transaction.atomic():  # Wrap transactions in an atomic block
            for _ in range(50):
                product = fake.random_element(elements=products)
                transaction_type = fake.random_element(elements=('sale', 'purchase'))
                quantity = fake.random_int(min=1, max=10)
                unit_price = product.price  # Use current product price

                if transaction_type == 'sale':
                    customer_name = fake.name()
                    supplier = None
                    stock_change = -quantity
                else:  # purchase
                    customer_name = None
                    supplier = fake.random_element(elements=suppliers)
                    stock_change = quantity

                transaction_id = fake.unique.lexify(text='TXN-????') # Generate unique transaction_id

                transaction = Transaction.objects.create(
                    product=product,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    customer_name=customer_name,
                    supplier=supplier,
                    total_amount = unit_price * quantity,  # Calculate total_amount
                    transaction_id=transaction_id # use the generated transaction_id
                )

                InventoryLog.objects.create(
                    product=product,
                    stock_change=stock_change,
                    reason=f"{transaction_type.capitalize()} Transaction",
                    source=transaction.transaction_id,
                    user=fake.random_element(elements=[admin_user, employee_user]) if User.objects.count() > 0 else None  # Random user
                )

                # Update stock_level using F() expressions for concurrency safety
                Product.objects.filter(pk=product.pk).update(stock_level=models.F('stock_level') + stock_change)

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))