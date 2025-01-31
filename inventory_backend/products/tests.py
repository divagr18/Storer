from django.test import TestCase
from .models import Product
from rest_framework.test import APITestCase
from rest_framework import status
class ProductModelTest(TestCase):
    def test_create_product(self):
        product = Product.objects.create(name="Laptop", category="Electronics", stock=10, price=999.99)
        self.assertEqual(product.name, "Laptop")
class ProductAPITest(APITestCase):
    def test_get_products(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)