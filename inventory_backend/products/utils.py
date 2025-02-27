# products/utils.py

from typing import TYPE_CHECKING
from datetime import date, timedelta
from django.utils import timezone
import numpy as np
from transactions.models import Transaction
from suppliers.models import Supplier

if TYPE_CHECKING:
    from products.models import Product

def calculate_reorder_point(product: 'Product', service_level: float = 0.95) -> int:
    """
    Calculates the reorder point for a product.

    Args:
        product: The Product object.
        service_level: Desired service level (probability of not stocking out during lead time).

    Returns:
        The calculated reorder point (integer).
    """
    # Retrieve lead time from the Supplier (or use a default if no supplier)
    lead_time_days = product.supplier.lead_time_days if product.supplier else 7  # Use 7 as a default if no supplier

    # Get forecast for the lead time
    forecasted_demand = get_forecasted_demand(product, lead_time_days)

    # Calculate safety stock (simplified - use a more sophisticated approach later)
    demand_std_dev = get_demand_std_dev(product, lead_time_days)

    from scipy.stats import norm
    z_score = norm.ppf(service_level)
    safety_stock = z_score * demand_std_dev  # A SIMPLE approach - improve this later

    reorder_point = forecasted_demand + safety_stock
    return max(0, int(reorder_point))  # Ensure ROP is not negative

def get_forecasted_demand(product: 'Product', lead_time_days: int) -> float:
    """
    Placeholder for fetching the demand forecast for the lead time. Replace this with your actual forecast logic
    using your existing Prophet or ARIMA code.

    Args:
        product: The Product object.
        lead_time_days: The lead time in days.

    Returns:
        The forecasted demand (float).
    """
    # Implement logic to fetch from ARIMA or Prophet
    # This example uses ARIMA

    import requests
    try:
        forecast_api_url = f"http://localhost:8000/api/products/{product.sku}/forecast/arima/{lead_time_days}/"  # Change to your actual URL

        response = requests.get(forecast_api_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        forecast_data = response.json()
        total_demand = sum(item['yhat'] for item in forecast_data['forecast'])

        return total_demand

    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return 0
    except KeyError as e:
        print(f"KeyError in parsing forecast API response {e}")
        return 0

def get_demand_std_dev(product: 'Product', lead_time_days: int) -> float:
    """
    Placeholder for calculating the standard deviation of demand based on historical data.

    Args:
        product: The Product object.
        lead_time_days: The lead time in days.

    Returns:
        The standard deviation of demand (float).
    """
    # Fetch historical sales data for the product for the last 3 months
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)

    sales_data = Transaction.objects.filter(
        product=product,
        transaction_date__range=[start_date, end_date]
    ).values_list('quantity', flat=True)

    if sales_data:
        demand_std_dev = np.std(sales_data)
        return demand_std_dev
    else:
        return 5  # Simplified placeholder - Replace with actual std dev calculation