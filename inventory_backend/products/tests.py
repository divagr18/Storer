from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from .models import Product

class ProductModelTest(TestCase):
    def setUp(self):
    # Clean up any pre-existing products
        Product.objects.all().delete()
        
        # Create one product only for this test
        self.product = Product.objects.create(
            name="Test Product", 
            description="Test Description", 
            price=10.99, 
            stock_level=100,
            category="Test Category"
        )
        
        self.url = '/api/products/'

    def test_product_creation(self):
        """Test that the product was created successfully."""
        product = self.product
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 10.99)
        self.assertEqual(product.stock_level, 100)
        self.assertEqual(product.category, "Test Category")
        self.assertIsNotNone(product.created_at)
        print("created")

    def test_product_str_method(self):
        """Test the string representation of the product."""
        product = self.product
        self.assertEqual(str(product), "Test Product")
        print("string")

class ProductAPITest(TestCase):
    def setUp(self):
    # Clean up any pre-existing products
        Product.objects.all().delete()
        
        # Create one product only for this test
        self.product = Product.objects.create(
            name="Test Product", 
            description="Test Description", 
            price=10.99, 
            stock_level=100,
            category="Test Category"
        )
        
        self.url = '/api/products/'


    def test_create_product(self):
        """Test that we can create a new product via the API."""
        data = {
            'name': 'New Product',
            'description': 'A brand new product',
            'price': 19.99,
            'stock_level': 50,
            'category': 'New Category'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(response.data['price'], str(data['price']))  # Ensure price is serialized as string
        print("created")

    def test_get_product(self):
        """Test that we can get the product details via the API."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ensure only 1 product is returned
        self.assertEqual(response.data[0]['name'], self.product.name)
        print("get")

    def test_delete_product(self):
        """Test that we can delete a product via the API."""
        response = self.client.delete(f'{self.url}{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())
        print("delete")
