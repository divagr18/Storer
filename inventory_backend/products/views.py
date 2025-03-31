from django.shortcuts import render

from rest_framework import status
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer
from django.db.models import Sum, Count
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
from django.db.models.functions import TruncMonth # Import TruncMonth
from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from products.models import Product
from transactions.models import Transaction
from .forecast import forecast_demand_prophet, forecast_demand_arima, backtest_prophet_forecast,backtest_arima_forecast # Import both forecast functions # Updated import
import pandas as pd
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
logger = logging.getLogger(__name__)

ForecastItemSchema = {
    'type': 'object',
    'properties': {
        'ds': {'type': 'string', 'format': 'date-time'}, # Or 'date' if only date part
        'yhat': {'type': 'number', 'format': 'float'},
        'yhat_lower': {'type': 'number', 'format': 'float'},
        'yhat_upper': {'type': 'number', 'format': 'float'},
        # Add other fields returned by your forecast functions if necessary
    }
}

MetricsSchema = {
    'type': 'object',
    'properties': {
        'mae': {'type': 'number', 'format': 'float'},
        'rmse': {'type': 'number', 'format': 'float'},
        # Add other metrics like mape etc. if returned
    }
}
@extend_schema( # <<< Add decorator
    responses={
        200: { # Define structure for successful response
            'type': 'object',
            'properties': {
                'product_details': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'}
                    }
                },
                'forecast': {
                    'type': 'array',
                    'items': ForecastItemSchema
                }
            }
        },
        404: OpenApiTypes.OBJECT, # Indicate other possible responses
        500: OpenApiTypes.OBJECT,
    },
    description='Retrieves a demand forecast for a product using Prophet.' # Add description
)
@api_view(['GET'])
def get_demand_forecast(request, product_sku, horizon):
    """
    API endpoint to retrieve a demand forecast for a product using Prophet.
    """
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    try:  # Wrap the database and data processing logic in a try block
        queryset = Transaction.objects.filter(product__sku=product_sku).order_by('transaction_date')
        transactions = list(queryset.values('transaction_date', 'quantity'))

        # Ensure timezone-naive datetimes for Prophet
        for transaction in transactions:
            if transaction['transaction_date']:
                transaction['transaction_date'] = transaction['transaction_date'].replace(tzinfo=None)

        df = pd.DataFrame(transactions)

        if df.empty:
            return Response({"error": "No historical transaction data found for this product."}, status=status.HTTP_404_NOT_FOUND)

        forecast = forecast_demand_prophet(product_sku, df, horizon)  # Calling Prophet function

        # Check if the forecast is empty or if the data is not a DataFrame
        if not forecast:  # Checks for an empty list, indicating that the forecast function failed
            return Response({"error": "Forecast is empty due to an error during prediction."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        product_details = {
            "name": product.name,
            "description": product.description,
        }

        return Response({"product_details": product_details, "forecast": forecast}, status=status.HTTP_200_OK) # no .to_dict() needed

    except Exception as e:  # Catch any unexpected errors
        logger.exception("An unexpected error occurred during the forecasting process.", exc_info=True)  # Log the full traceback
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@extend_schema( # <<< Add decorator
    parameters=[ # Define path and query parameters
        OpenApiParameter('product_sku', OpenApiTypes.STR, OpenApiParameter.PATH, required=True, description='SKU of the product'),
        OpenApiParameter('horizon', OpenApiTypes.INT, OpenApiParameter.PATH, required=True, description='Forecast horizon in periods (e.g., days)'),
        OpenApiParameter('arima_order_str', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='Optional ARIMA order as p,d,q (e.g., \'5,1,0\')'),
    ],
    responses={
        200: { # Define structure for successful response
            'type': 'object',
            'properties': {
                'product_details': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'}
                    }
                },
                'forecast': {
                    'type': 'array',
                    'items': ForecastItemSchema
                },
                'arima_order_used': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'example': [5, 1, 0]
                }
            }
        },
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    description='Retrieves a demand forecast for a product using ARIMA.' # Add description
)

@api_view(['GET'])
def get_arima_demand_forecast(request, product_sku, horizon, arima_order_str=None):
    """
    API endpoint to retrieve a demand forecast for a product using ARIMA, with enhanced logging.
    """
    logger.info(f"Starting ARIMA forecast API request for SKU: {product_sku}, horizon: {horizon}, order_str: {arima_order_str}") # Log request start

    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        logger.warning(f"Product with SKU '{product_sku}' not found.") # Log product not found
        return Response({"error": "Product not found."}, status=404)

    queryset = Transaction.objects.filter(product__sku=product_sku).order_by('transaction_date')
    transactions = list(queryset.values('transaction_date', 'quantity'))
    logger.info(f"Retrieved {len(transactions)} transactions from database for SKU: {product_sku}") # Log transaction count

    for transaction in transactions:
        if transaction['transaction_date']:
            transaction['transaction_date'] = transaction['transaction_date'].replace(tzinfo=None)

    df = pd.DataFrame(transactions)
    logger.info(f"Pandas DataFrame created. Shape: {df.shape}") # Log DataFrame shape

    if df.empty:
        logger.warning(f"No transaction data after DataFrame creation for SKU '{product_sku}'.") # Log empty DataFrame
        return Response({"error": "No historical transaction data found for this product."}, status=404)

    try:
        arima_order = (5,1,0) # Default order
        if arima_order_str:
            try:
                p, d, q = map(int, arima_order_str.split(','))
                arima_order = (p, d, q)
            except ValueError as ve:
                logger.warning(f"Invalid arima_order format: {arima_order_str}. Error: {ve}") # Log invalid order format
                return Response({"error": "Invalid arima_order format. Use 'p,d,q' (e.g., '2,1,2')."}, status=400)

        logger.info(f"Calling forecast_demand_arima with SKU: {product_sku}, horizon: {horizon}, order: {arima_order}, DataFrame shape: {df.shape}") # Log before forecast call # Log DataFrame shape
        forecast = forecast_demand_arima(product_sku, df, horizon, arima_order=arima_order)

        forecast_list = forecast.to_dict('records')
        product_details = {
            "name": product.name,
            "description": product.description,
        }
        logger.info(f"ARIMA forecast generated successfully for SKU: {product_sku}, horizon: {horizon}, order: {arima_order}") # Log success
        return Response({"product_details": product_details, "forecast": forecast_list, "arima_order_used": arima_order})

    except Exception as e:
        logger.error(f"ARIMA forecasting failed for SKU {product_sku}, order: {arima_order}. Error: {e}", exc_info=True) # Log full exception # Log full exception
        return Response({"error": f"ARIMA forecasting failed: {str(e)}"}, status=500)
@extend_schema( # <<< Add decorator
    responses={
        200: { # Define structure for successful response
            'type': 'object',
            'properties': {
                'product_details': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'}
                    }
                },
                'metrics': MetricsSchema,
                'forecast': {
                    'type': 'array',
                    'items': ForecastItemSchema
                }
            }
        },
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    description='Performs backtesting for Prophet demand forecast and retrieves evaluation metrics.' # Add description
)
@api_view(['GET'])
def get_prophet_backtesting(request, product_sku, validation_horizon):
    """
    API endpoint to perform backtesting for Prophet demand forecast and retrieve evaluation metrics.
    """
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    try:  # Wrap the database and data processing logic in a try block
        queryset = Transaction.objects.filter(product__sku=product_sku).order_by('transaction_date')
        transactions = list(queryset.values('transaction_date', 'quantity'))

        # Ensure timezone-naive datetimes for Prophet
        for transaction in transactions:
            if transaction['transaction_date']:
                transaction['transaction_date'] = transaction['transaction_date'].replace(tzinfo=None)

        df = pd.DataFrame(transactions)

        if df.empty:
            return Response({"error": "No historical transaction data found for this product."}, status=status.HTTP_404_NOT_FOUND)

        try:
            validation_horizon_int = int(validation_horizon)  # Convert horizon to integer

            if validation_horizon_int <= 0:  # Validate horizon
                return Response({"error": "Validation horizon must be a positive integer."},
                                status=status.HTTP_400_BAD_REQUEST)

            backtest_results = backtest_prophet_forecast(product_sku, df.copy(), validation_horizon_int)  # Call backtesting function # Pass a COPY

            if "error" in backtest_results:  # Check for errors from backtesting
                return Response({"error": backtest_results["error"]}, status=status.HTTP_400_BAD_REQUEST)  # Return backtesting error to client # Return backtesting error

            metrics = backtest_results["metrics"]  # Extract metrics from results
            forecast_list = backtest_results["forecast"]  # Extract forecast from results

            product_details = {
                "name": product.name,
                "description": product.description,
            }
            return Response({"product_details": product_details, "metrics": metrics, "forecast": forecast_list},
                            status=status.HTTP_200_OK)  # Include metrics in API response # Include metrics in response

        except ValueError:  # Handle invalid horizon input
            return Response({"error": "Invalid validation_horizon. Must be an integer."},
                            status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception(f"Prophet backtesting API error for SKU {product_sku}, horizon: {validation_horizon}. "
                         f"Error: {e}", exc_info=True)  # Log full exception

        return Response({"error": f"Prophet backtesting failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema( # <<< Add decorator
    parameters=[ # Define path and query parameters
        OpenApiParameter('product_sku', OpenApiTypes.STR, OpenApiParameter.PATH, required=True, description='SKU of the product'),
        OpenApiParameter('validation_horizon', OpenApiTypes.INT, OpenApiParameter.PATH, required=True, description='Backtesting horizon in periods (e.g., days)'),
        OpenApiParameter('arima_order_str', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='Optional ARIMA order as p,d,q (e.g., \'5,1,0\')'),
    ],
    responses={
        200: { # Define structure for successful response
            'type': 'object',
            'properties': {
                'product_details': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'}
                    }
                },
                'metrics': MetricsSchema,
                'forecast': {
                    'type': 'array',
                    'items': ForecastItemSchema
                },
                'arima_order_used': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'example': [5, 1, 0]
                }
            }
        },
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    description='Performs backtesting for ARIMA demand forecast and retrieves evaluation metrics.' # Add description
)
@api_view(['GET'])
def get_arima_backtesting(request, product_sku, validation_horizon, arima_order_str=None): # New ARIMA Backtesting View
    """
    API endpoint to perform backtesting for ARIMA demand forecast and retrieve evaluation metrics.
    Enhanced logging to debug validation_horizon.
    """
    logger.info(f"ARIMA Backtesting API: Request Received - SKU: {product_sku}, horizon_str: {validation_horizon}, order_str: {arima_order_str}") # Log initial request info

    logger.info(f"Value of validation_horizon at view entry: {validation_horizon}, Type: {type(validation_horizon)}") # Log validation_horizon VALUE and TYPE right away # Log validation_horizon and its type

    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=404)

    queryset = Transaction.objects.filter(product__sku=product_sku).order_by('transaction_date')
    transactions = list(queryset.values('transaction_date', 'quantity'))
    for transaction in transactions:
        if transaction['transaction_date']:
            transaction['transaction_date'] = transaction['transaction_date'].replace(tzinfo=None)
    df = pd.DataFrame(transactions)
    if df.empty:
        return Response({"error": "No historical transaction data found for this product."}, status=404)

    try:
        validation_horizon_int = int(validation_horizon) # Attempt int conversion

        logger.info(f"Value of validation_horizon BEFORE int conversion: {validation_horizon}, Type: {type(validation_horizon)}") # Log BEFORE conversion # Log before int conversion

        if validation_horizon_int <= 0:
            return Response({"error": "Validation horizon must be a positive integer."}, status=400)

        arima_order = (5,1,0) # Default ARIMA order
        if arima_order_str: # If order is passed via API
            try:
                p, d, q = map(int, arima_order_str.split(','))
                arima_order = (p, d, q)
            except ValueError:
                return Response({"error": "Invalid arima_order format. Use 'p,d,q' (e.g., '2,1,2')."}, status=400)


        backtest_results = backtest_arima_forecast(product_sku, df, validation_horizon_int, arima_order=arima_order) # Call ARIMA backtesting function

        if "error" in backtest_results:
            return Response({"error": backtest_results["error"]}, status=400)

        metrics = backtest_results["metrics"]
        forecast_list = backtest_results["forecast"]
        arima_order_used = backtest_results["arima_order_used"]

        product_details = {
            "name": product.name,
            "description": product.description,
        }
        return Response({"product_details": product_details, "metrics": metrics, "forecast": forecast_list, "arima_order_used": arima_order_used})

    except ValueError as ve: # Catch ValueError during int(validation_horizon) # Catch ValueError specifically
        logger.error(f"ValueError during int(validation_horizon): Value: '{validation_horizon}', Error: {ve}", exc_info=True) # Log ValueError details # Log ValueError
        return Response({"error": "Invalid validation_horizon. Must be an integer."}, status=400)
    except Exception as e:
        logger.error(f"ARIMA backtesting API error for SKU {product_sku}, horizon: {validation_horizon}, order: {arima_order}. Error: {e}", exc_info=True)
        return Response({"error": f"ARIMA backtesting failed: {str(e)}"}, status=500)
    
@extend_schema( # <<< Add decorator
    parameters=[ # Define optional path parameter
        OpenApiParameter('product_sku', OpenApiTypes.STR, OpenApiParameter.PATH, required=False, description='Optional SKU to filter metrics for a specific product.'),
    ],
    responses={
        200: { # Define structure for successful response
            'type': 'object',
            'properties': {
                'total_sales': {'type': 'number', 'format': 'float'},
                'total_profit': {'type': 'number', 'format': 'float'},
                'total_transactions': {'type': 'integer'},
                'total_products': {'type': 'integer'},
            },
            'example': { # Add an example
                 "total_sales": 12550.75,
                 "total_profit": 3150.50,
                 "total_transactions": 450,
                 "total_products": 58
             }
        },
        404: OpenApiTypes.OBJECT, # If product_sku is provided but not found
        500: OpenApiTypes.OBJECT,
    },
    description='Retrieves dashboard metrics (Total Sales, Profit, Transactions, Products), optionally filtered by product SKU.' # Add description
)    
@api_view(['GET'])
def get_dashboard_metrics(request, product_sku=None): # Make product_sku optional
    """
    API endpoint to retrieve dashboard metrics (Total Sales, Total Profit, Total Transactions, Total Products),
    optionally filtered by product SKU.
    """
    try:
        # Base queryset for transactions
        transaction_queryset = Transaction.objects.filter(transaction_type='sale')

        # Apply product SKU filter if provided
        if product_sku:
            try:
                product = Product.objects.get(sku=product_sku)
            except Product.DoesNotExist:
                return Response({"error": "Product not found."}, status=404)
            transaction_queryset = transaction_queryset.filter(product=product)

        # Calculate Total Sales
        total_sales = transaction_queryset.aggregate(total=Sum('total_amount'))['total'] or 0

        # Calculate Total Profit (Assuming cost_price is stored on Product)
        total_revenue = transaction_queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        total_cost = Transaction.objects.filter(transaction_type='purchase').aggregate(total=Sum('total_amount'))['total'] or 0
        total_profit = total_revenue - total_cost

        # Calculate Total Transactions (Orders)
        total_transactions = transaction_queryset.count()

        # Calculate Total Products
        total_products = Product.objects.count()

        # Construct the response
        metrics = {
            "total_sales": total_sales,
            "total_profit": total_profit,
            "total_transactions": total_transactions,
            "total_products": total_products,
        }

        return Response(metrics) # Return the metrics in a JSON response

    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {e}", exc_info=True)
        return Response({"error": f"Failed to calculate dashboard metrics: {str(e)}"}, status=500)
@extend_schema( # <<< Add decorator
    parameters=[ # Define optional path parameter
        OpenApiParameter('product_sku', OpenApiTypes.STR, OpenApiParameter.PATH, required=False, description='Optional SKU to filter trend for a specific product.'),
    ],
    responses={
        200: { # Define structure for successful response - array of objects
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'month': {'type': 'string', 'format': 'date'}, # Or date-time if time part is relevant
                    'total_sales': {'type': 'number', 'format': 'float'},
                    'total_profit': {'type': 'number', 'format': 'float'},
                }
            },
            'example': [ # Add an example
                {"month": "2024-01-01", "total_sales": 5000.00, "total_profit": 1200.50},
                {"month": "2024-02-01", "total_sales": 7550.75, "total_profit": 1950.00}
            ]
        },
        404: OpenApiTypes.OBJECT, # If product_sku is provided but not found
        500: OpenApiTypes.OBJECT,
    },
    description='Retrieves monthly sales and profit trend data, optionally filtered by product SKU.' # Add description
)    
@api_view(['GET'])
def get_sales_profit_trend(request, product_sku=None):
    """
    API endpoint to retrieve sales and profit trend data (monthly) for a product.
    """
    try:
        # Base queryset for transactions (sales only)
        transaction_queryset = Transaction.objects.filter(transaction_type='sale')
        purchase_queryset = Transaction.objects.filter(transaction_type='purchase') # New purchase queryset

        # Apply product SKU filter if provided
        if product_sku:
            try:
                product = Product.objects.get(sku=product_sku)
            except Product.DoesNotExist:
                return Response({"error": "Product not found."}, status=404)
            transaction_queryset = transaction_queryset.filter(product=product)
            purchase_queryset = purchase_queryset.filter(product=product) # Filter purchase queryset too # Filter purchase queryset too

        # Aggregate sales and profit by month
        sales_profit_data = transaction_queryset.annotate(month=TruncMonth('transaction_date')).values('month').annotate(
            total_sales=Sum('total_amount'),
            total_profit=Sum(models.F('total_amount') - models.F('unit_price') * models.F('quantity')) #total_amount is the sales price, and cost price is the cost price
        ).order_by('month')

        total_cost = purchase_queryset.aggregate(total=Sum('total_amount'))['total'] or 0

        # Convert to list of dictionaries for JSON serialization
        sales_profit_list = list(sales_profit_data)

        return Response(sales_profit_list) # Return the data in a JSON response

    except Exception as e:
        logger.error(f"Error calculating sales and profit trend: {e}", exc_info=True)
        return Response({"error": f"Failed to calculate sales and profit trend: {str(e)}"}, status=500)