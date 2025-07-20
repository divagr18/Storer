from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from .models import Product


class ProductModelTest(TestCase):
    def setUp(self):
        """Sets up the test environment by removing all existing Product entries and creating a single test product.

        This method clears the Product database table to ensure a clean state before each test. It then creates a single Product instance with predefined attributes, which can be used in the test cases. Additionally, it sets the base URL for product API endpoints.

        Attributes set:
            self.product: The newly created Product instance used for testing.
            self.url: The API endpoint URL for product-related requests."""
        Product.objects.all().delete()
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.99,
            stock_level=100,
            category="Test Category",
        )
        self.url = "/api/products/"

    def test_product_creation(self):
        """Tests that a product instance is created with the correct attributes.

        Verifies that the product's name, price, stock level, and category match expected values,
        and that the creation timestamp is set. Prints a confirmation message upon successful completion."""
        product = self.product
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 10.99)
        self.assertEqual(product.stock_level, 100)
        self.assertEqual(product.category, "Test Category")
        self.assertIsNotNone(product.created_at)
        print("created")

    def test_product_str_method(self):
        """Test that the string representation of a Product instance returns the expected name.

        Verifies that calling str() on the product object returns the string 'Test Product'.
        Assumes self.product is a Product instance initialized with the name 'Test Product'.

        No return value."""
        product = self.product
        self.assertEqual(str(product), "Test Product")
        print("string")


class ProductAPITest(TestCase):
    def setUp(self):
        """Sets up the test environment by clearing existing products and creating a single test product.

        This method is called before each test method to ensure a consistent starting state.
        It deletes all existing Product records, then creates a new Product instance with predefined attributes.
        Additionally, it sets the base URL for product-related API endpoints.

        Attributes set:
        - self.product: the newly created Product instance.
        - self.url: the API endpoint URL string for products."""
        Product.objects.all().delete()
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.99,
            stock_level=100,
            category="Test Category",
        )
        self.url = "/api/products/"

    def test_create_product(self):
        """Test creating a new product through the API endpoint.

        Sends a POST request with product details to the product creation URL and verifies that the response
        has a 201 CREATED status code and that the returned product data matches the input data, including
        correct serialization of the price field as a string."""
        data = {
            "name": "New Product",
            "description": "A brand new product",
            "price": 19.99,
            "stock_level": 50,
            "category": "New Category",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["price"], str(data["price"]))
        print("created")

    def test_get_product(self):
        """Test retrieving product details through the API.

        Makes a GET request to the product endpoint and verifies that the response status is 200 OK,
        exactly one product is returned, and the product name matches the expected product.

        Returns:
            None"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], self.product.name)
        print("get")

    def test_delete_product(self):
        """Test that a product can be successfully deleted via the API.

        Sends a DELETE request to the product detail endpoint of the API and verifies
        that the response status code is 204 NO CONTENT. Also confirms that the product
        is no longer present in the database after deletion.

        No arguments or return values; this is a unit test method."""
        response = self.client.delete(f"{self.url}{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())
        print("delete")
