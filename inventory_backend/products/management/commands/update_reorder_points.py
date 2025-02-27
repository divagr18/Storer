# products/management/commands/update_reorder_points.py

from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Updates the reorder points for all products.'

    def handle(self, *args, **options):
        products = Product.objects.all()
        for product in products:
            product.update_reorder_point()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated reorder point for {product.name} to {product.reorder_point}'))

        self.stdout.write(self.style.SUCCESS('Successfully updated reorder points for all products.'))