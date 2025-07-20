import semantic_kernel as sk
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from products.models import Product
import logging

logger = logging.getLogger(__name__)


class InventoryPlugin:
    """
    A Semantic Kernel Plugin that provides functions to interact with inventory data.
    The descriptions and names provided to @kernel_function are crucial for the AI
    to understand how and when to use these functions.
    """

    @kernel_function(
        description="Retrieves the current stock level for a single product given its SKU.",
        name="get_product_stock_level",
    )
    def get_product_stock_level(self, product_sku: str) -> str:
        """Retrieve the current stock level for a given product SKU from the inventory database.

        Args:
            product_sku (str): The Stock Keeping Unit (SKU) identifier of the product to look up.

        Returns:
            str: A descriptive message indicating the stock level of the product,
                 or an error message if the SKU is missing, the product is not found,
                 or an unexpected error occurs during retrieval."""
        logger.info(
            f"SK Native Function 'get_product_stock_level' called with SKU: {product_sku}"
        )
        if not product_sku:
            return "Please provide a product SKU."
        try:
            product = Product.objects.get(sku=product_sku)
            logger.info(f"Found product: {product.name}, Stock: {product.stock_level}")
            return f"The current stock level for product SKU {product_sku} ({product.name}) is {product.stock_level} units."
        except Product.DoesNotExist:
            logger.warning(f"Product with SKU {product_sku} not found in database.")
            return f"Sorry, I couldn't find a product with the SKU '{product_sku}'."
        except Exception as e:
            logger.error(
                f"Error in get_product_stock_level for SKU {product_sku}: {e}",
                exc_info=True,
            )
            return f"An unexpected error occurred while trying to retrieve the stock level for SKU {product_sku}."
