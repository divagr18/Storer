from django.shortcuts import render


from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

from rest_framework.decorators import api_view
from rest_framework.response import Response
from products.models import Product
from transactions.models import Transaction
from .forecast import forecast_demand_prophet, forecast_demand_arima, backtest_prophet_forecast,backtest_arima_forecast # Import both forecast functions # Updated import
import pandas as pd
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_demand_forecast(request, product_sku, horizon):
    """
    API endpoint to retrieve a demand forecast for a product using Prophet.
    """
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
        forecast = forecast_demand_prophet(product_sku, df, horizon) # Calling Prophet function

        forecast_list = forecast.to_dict('records')
        product_details = {
            "name": product.name,
            "description": product.description,
        }
        return Response({"product_details": product_details, "forecast": forecast_list})

    except Exception as e:
        return Response({"error": f"Prophet forecasting failed: {str(e)}"}, status=500)
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
@api_view(['GET'])
def get_prophet_backtesting(request, product_sku, validation_horizon): # New backtesting API view # New backtesting API view
    """
    API endpoint to perform backtesting for Prophet demand forecast and retrieve evaluation metrics.
    """
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
        validation_horizon_int = int(validation_horizon) # Convert horizon to integer

        if validation_horizon_int <= 0: # Validate horizon
            return Response({"error": "Validation horizon must be a positive integer."}, status=400)

        backtest_results = backtest_prophet_forecast(product_sku, df, validation_horizon_int) # Call backtesting function # Call backtesting function

        if "error" in backtest_results: # Check for errors from backtesting
            return Response({"error": backtest_results["error"]}, status=400) # Return backtesting error to client # Return backtesting error

        metrics = backtest_results["metrics"] # Extract metrics from results
        forecast_list = backtest_results["forecast"] # Extract forecast from results

        product_details = {
            "name": product.name,
            "description": product.description,
        }
        return Response({"product_details": product_details, "metrics": metrics, "forecast": forecast_list}) # Include metrics in API response # Include metrics in response

    except ValueError: # Handle invalid horizon input
        return Response({"error": "Invalid validation_horizon. Must be an integer."}, status=400)
    except Exception as e:
        logger.error(f"Prophet backtesting API error for SKU {product_sku}, horizon: {validation_horizon}. Error: {e}", exc_info=True) # Log full exception
        return Response({"error": f"Prophet backtesting failed: {str(e)}"}, status=500)


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