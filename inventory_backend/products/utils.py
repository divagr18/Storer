from typing import TYPE_CHECKING
from datetime import date, timedelta
from django.utils import timezone
import numpy as np
from transactions.models import Transaction
from suppliers.models import Supplier

if TYPE_CHECKING:
    from products.models import Product


def calculate_reorder_point(product: "Product", service_level: float = 0.95) -> int:
    """Calculates the reorder point for a product based on forecasted demand, demand variability, and desired service level.

    Args:
        product: The Product instance for which to calculate the reorder point. Must have an associated supplier with lead time information.
        service_level: The target probability (between 0 and 1) of not experiencing a stockout during the supplier lead time. Defaults to 0.95.

    Returns:
        int: The reorder point as an integer, representing the inventory level at which a new order should be placed to maintain the desired service level."""
    lead_time_days = product.supplier.lead_time_days if product.supplier else 7
    forecasted_demand = get_forecasted_demand(product, lead_time_days)
    demand_std_dev = get_demand_std_dev(product, lead_time_days)
    from scipy.stats import norm

    z_score = norm.ppf(service_level)
    safety_stock = z_score * demand_std_dev
    reorder_point = forecasted_demand + safety_stock
    return max(0, int(reorder_point))


def get_forecasted_demand(product: "Product", lead_time_days: int) -> float:
    """Fetch the forecasted demand for a product over a specified lead time using an external API.

    Args:
        product (Product): Product instance with a 'sku' attribute identifying the product.
        lead_time_days (int): Number of days ahead for which to forecast demand.

    Returns:
        float: Total forecasted demand summed over the lead time period. Returns 0 if the API request fails or the response cannot be parsed."""
    import requests

    try:
        forecast_api_url = f"http://localhost:8000/api/products/{product.sku}/forecast/arima/{lead_time_days}/"
        response = requests.get(forecast_api_url)
        response.raise_for_status()
        forecast_data = response.json()
        total_demand = sum(item["yhat"] for item in forecast_data["forecast"])
        return total_demand
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return 0
    except KeyError as e:
        print(f"KeyError in parsing forecast API response {e}")
        return 0


def get_demand_std_dev(product: "Product", lead_time_days: int) -> float:
    """Calculates the standard deviation of product demand over the past 90 days.

    Args:
        product (Product): The product for which to calculate demand variability.
        lead_time_days (int): The lead time in days (currently unused in calculation).

    Returns:
        float: The standard deviation of demand quantity based on historical transactions;
               returns a default value of 5 if no sales data is available."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    sales_data = Transaction.objects.filter(
        product=product, transaction_date__range=[start_date, end_date]
    ).values_list("quantity", flat=True)
    if sales_data:
        demand_std_dev = np.std(sales_data)
        return demand_std_dev
    else:
        return 5
