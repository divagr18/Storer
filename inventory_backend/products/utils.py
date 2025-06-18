from typing import TYPE_CHECKING
from datetime import date, timedelta
from django.utils import timezone
import numpy as np
from transactions.models import Transaction
from suppliers.models import Supplier
if TYPE_CHECKING:
    from products.models import Product


def calculate_reorder_point(product: 'Product', service_level: float=0.95
    ) ->int:
    """
    Calculates the reorder point for a product.

    Args:
        product: The Product object.
        service_level: Desired service level (probability of not stocking out during lead time).

    Returns:
        The calculated reorder point (integer).
    """
    lead_time_days = product.supplier.lead_time_days if product.supplier else 7
    forecasted_demand = get_forecasted_demand(product, lead_time_days)
    demand_std_dev = get_demand_std_dev(product, lead_time_days)
    from scipy.stats import norm
    z_score = norm.ppf(service_level)
    safety_stock = z_score * demand_std_dev
    reorder_point = forecasted_demand + safety_stock
    return max(0, int(reorder_point))


def get_forecasted_demand(product: 'Product', lead_time_days: int) ->float:
    """Fetches the forecasted demand for a given product over a specified lead time using an external forecasting API.

Args:
    product (Product): The product for which the demand forecast is requested. Must have a 'sku' attribute.
    lead_time_days (int): The lead time in days over which to forecast demand.

Returns:
    float: The total forecasted demand for the product over the lead time. Returns 0 if the forecast cannot be retrieved or parsed."""
    import requests
    try:
        forecast_api_url = (
            f'http://localhost:8000/api/products/{product.sku}/forecast/arima/{lead_time_days}/'
            )
        response = requests.get(forecast_api_url)
        response.raise_for_status()
        forecast_data = response.json()
        total_demand = sum(item['yhat'] for item in forecast_data['forecast'])
        return total_demand
    except requests.exceptions.RequestException as e:
        print(f'Error fetching forecast: {e}')
        return 0
    except KeyError as e:
        print(f'KeyError in parsing forecast API response {e}')
        return 0


def get_demand_std_dev(product: 'Product', lead_time_days: int) ->float:
    """
    Placeholder for calculating the standard deviation of demand based on historical data.

    Args:
        product: The Product object.
        lead_time_days: The lead time in days.

    Returns:
        The standard deviation of demand (float).
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    sales_data = Transaction.objects.filter(product=product,
        transaction_date__range=[start_date, end_date]).values_list('quantity',
        flat=True)
    if sales_data:
        demand_std_dev = np.std(sales_data)
        return demand_std_dev
    else:
        return 5
