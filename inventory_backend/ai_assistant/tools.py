import semantic_kernel as sk
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from products.models import Product # Import your Product model
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
        name="get_product_stock_level" # The name the AI will use to call this function
    )
    def get_product_stock_level(
        self,
        product_sku: str # Type hints help define the expected input parameter(s)
    ) -> str: # The return type hint
        """
        Native function to get stock level.

        Args:
            product_sku (str): The Stock Keeping Unit (SKU) of the product to query.

        Returns:
            str: A human-readable string describing the stock level,
                 or an error message if the product is not found or an issue occurs.
        """
        logger.info(f"SK Native Function 'get_product_stock_level' called with SKU: {product_sku}")
        if not product_sku:
            return "Please provide a product SKU."
        try:
            # Access the Django model to get the product
            product = Product.objects.get(sku=product_sku)
            logger.info(f"Found product: {product.name}, Stock: {product.stock_level}")
            # Return a descriptive string
            return f"The current stock level for product SKU {product_sku} ({product.name}) is {product.stock_level} units."
        except Product.DoesNotExist:
            logger.warning(f"Product with SKU {product_sku} not found in database.")
            return f"Sorry, I couldn't find a product with the SKU '{product_sku}'."
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Error in get_product_stock_level for SKU {product_sku}: {e}", exc_info=True)
            return f"An unexpected error occurred while trying to retrieve the stock level for SKU {product_sku}."

    # --- You can add more native functions to this plugin later ---
    # Example:
    # @kernel_function(description="Suggests if a product needs reordering", name="suggest_reorder")
    # def suggest_product_reorder(self, product_sku: str) -> str:
    #     # Implementation using product.reorder_point, product.stock_level etc.
    #     pass