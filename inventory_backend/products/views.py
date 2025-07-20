from django.shortcuts import render
from rest_framework import status
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer
from django.db.models import Sum, Count


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


from django.db.models.functions import TruncMonth
from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from products.models import Product
from transactions.models import Transaction
from .forecast import (
    forecast_demand_prophet,
    forecast_demand_arima,
    backtest_prophet_forecast,
    backtest_arima_forecast,
)
import pandas as pd
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger(__name__)
ForecastItemSchema = {
    "type": "object",
    "properties": {
        "ds": {"type": "string", "format": "date-time"},
        "yhat": {"type": "number", "format": "float"},
        "yhat_lower": {"type": "number", "format": "float"},
        "yhat_upper": {"type": "number", "format": "float"},
    },
}
MetricsSchema = {
    "type": "object",
    "properties": {
        "mae": {"type": "number", "format": "float"},
        "rmse": {"type": "number", "format": "float"},
    },
}


@extend_schema(
    responses={
        (200): {
            "type": "object",
            "properties": {
                "product_details": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
                "forecast": {"type": "array", "items": ForecastItemSchema},
            },
        },
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Retrieves a demand forecast for a product using Prophet.",
)
@api_view(["GET"])
def get_demand_forecast(request, product_sku, horizon):
    """Retrieve a demand forecast for a specified product over a given time horizon using the Prophet model.

    Args:
        request (HttpRequest): The HTTP request object.
        product_sku (str): The SKU identifier for the product whose demand forecast is requested.
        horizon (int): The number of future periods to forecast.

    Returns:
        Response: A DRF Response object containing either:
            - HTTP 200 with a JSON payload including product details and forecast data,
            - HTTP 404 if the product or its historical transaction data is not found,
            - HTTP 500 if an error occurs during forecasting or unexpected exceptions are raised.

    This view queries transaction data for the product, prepares it for time series forecasting,
    calls the Prophet-based forecast function, and handles potential errors gracefully."""
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        queryset = Transaction.objects.filter(product__sku=product_sku).order_by(
            "transaction_date"
        )
        transactions = list(queryset.values("transaction_date", "quantity"))
        for transaction in transactions:
            if transaction["transaction_date"]:
                transaction["transaction_date"] = transaction[
                    "transaction_date"
                ].replace(tzinfo=None)
        df = pd.DataFrame(transactions)
        if df.empty:
            return Response(
                {"error": "No historical transaction data found for this product."},
                status=status.HTTP_404_NOT_FOUND,
            )
        forecast = forecast_demand_prophet(product_sku, df, horizon)
        if not forecast:
            return Response(
                {"error": "Forecast is empty due to an error during prediction."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        product_details = {"name": product.name, "description": product.description}
        return Response(
            {"product_details": product_details, "forecast": forecast},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.exception(
            "An unexpected error occurred during the forecasting process.",
            exc_info=True,
        )
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "product_sku",
            OpenApiTypes.STR,
            OpenApiParameter.PATH,
            required=True,
            description="SKU of the product",
        ),
        OpenApiParameter(
            "horizon",
            OpenApiTypes.INT,
            OpenApiParameter.PATH,
            required=True,
            description="Forecast horizon in periods (e.g., days)",
        ),
        OpenApiParameter(
            "arima_order_str",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            required=False,
            description="Optional ARIMA order as p,d,q (e.g., '5,1,0')",
        ),
    ],
    responses={
        (200): {
            "type": "object",
            "properties": {
                "product_details": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
                "forecast": {"type": "array", "items": ForecastItemSchema},
                "arima_order_used": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "example": [5, 1, 0],
                },
            },
        },
        (400): OpenApiTypes.OBJECT,
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Retrieves a demand forecast for a product using ARIMA.",
)
@api_view(["GET"])
def get_arima_demand_forecast(request, product_sku, horizon, arima_order_str=None):
    """Handles an API request to generate a demand forecast for a specified product SKU using an ARIMA model.

    Args:
        request (HttpRequest): The HTTP request object.
        product_sku (str): The SKU identifier of the product to forecast.
        horizon (int): The number of future periods to forecast.
        arima_order_str (str, optional): Comma-separated string specifying the ARIMA order (p,d,q).
            Defaults to None, which uses the default order (5,1,0).

    Returns:
        Response: A DRF Response object containing product details and forecast results in case of success,
            or an error message with appropriate HTTP status code if the product is not found,
            transaction data is missing, ARIMA order format is invalid, or forecasting fails.

    Logs detailed information about the request processing, including data retrieval, parameter parsing,
    forecasting steps, and any errors encountered."""
    logger.info(
        f"Starting ARIMA forecast API request for SKU: {product_sku}, horizon: {horizon}, order_str: {arima_order_str}"
    )
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        logger.warning(f"Product with SKU '{product_sku}' not found.")
        return Response({"error": "Product not found."}, status=404)
    queryset = Transaction.objects.filter(product__sku=product_sku).order_by(
        "transaction_date"
    )
    transactions = list(queryset.values("transaction_date", "quantity"))
    logger.info(
        f"Retrieved {len(transactions)} transactions from database for SKU: {product_sku}"
    )
    for transaction in transactions:
        if transaction["transaction_date"]:
            transaction["transaction_date"] = transaction["transaction_date"].replace(
                tzinfo=None
            )
    df = pd.DataFrame(transactions)
    logger.info(f"Pandas DataFrame created. Shape: {df.shape}")
    if df.empty:
        logger.warning(
            f"No transaction data after DataFrame creation for SKU '{product_sku}'."
        )
        return Response(
            {"error": "No historical transaction data found for this product."},
            status=404,
        )
    try:
        arima_order = 5, 1, 0
        if arima_order_str:
            try:
                p, d, q = map(int, arima_order_str.split(","))
                arima_order = p, d, q
            except ValueError as ve:
                logger.warning(
                    f"Invalid arima_order format: {arima_order_str}. Error: {ve}"
                )
                return Response(
                    {
                        "error": "Invalid arima_order format. Use 'p,d,q' (e.g., '2,1,2')."
                    },
                    status=400,
                )
        logger.info(
            f"Calling forecast_demand_arima with SKU: {product_sku}, horizon: {horizon}, order: {arima_order}, DataFrame shape: {df.shape}"
        )
        forecast = forecast_demand_arima(
            product_sku, df, horizon, arima_order=arima_order
        )
        forecast_list = forecast.to_dict("records")
        product_details = {"name": product.name, "description": product.description}
        logger.info(
            f"ARIMA forecast generated successfully for SKU: {product_sku}, horizon: {horizon}, order: {arima_order}"
        )
        return Response(
            {
                "product_details": product_details,
                "forecast": forecast_list,
                "arima_order_used": arima_order,
            }
        )
    except Exception as e:
        logger.error(
            f"ARIMA forecasting failed for SKU {product_sku}, order: {arima_order}. Error: {e}",
            exc_info=True,
        )
        return Response({"error": f"ARIMA forecasting failed: {str(e)}"}, status=500)


@extend_schema(
    responses={
        (200): {
            "type": "object",
            "properties": {
                "product_details": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
                "metrics": MetricsSchema,
                "forecast": {"type": "array", "items": ForecastItemSchema},
            },
        },
        (400): OpenApiTypes.OBJECT,
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Performs backtesting for Prophet demand forecast and retrieves evaluation metrics.",
)
@api_view(["GET"])
def get_prophet_backtesting(request, product_sku, validation_horizon):
    """Handles a REST API request to perform backtesting of Prophet demand forecasting for a given product SKU.

    Args:
        request (HttpRequest): The HTTP request object.
        product_sku (str): The SKU identifier of the product to backtest.
        validation_horizon (str|int): The validation horizon as a positive integer, specifying the number of periods to use for backtesting.

    Returns:
        Response: An HTTP response containing either:
            - On success (HTTP 200): JSON with product details, forecasting metrics, and forecast results.
            - On failure (HTTP 4xx or 5xx): JSON with an "error" message explaining the cause, such as product not found,
              invalid horizon input, missing historical data, or backtesting errors.

    Raises:
        Does not raise exceptions directly; all errors are caught and returned as HTTP responses."""
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        queryset = Transaction.objects.filter(product__sku=product_sku).order_by(
            "transaction_date"
        )
        transactions = list(queryset.values("transaction_date", "quantity"))
        for transaction in transactions:
            if transaction["transaction_date"]:
                transaction["transaction_date"] = transaction[
                    "transaction_date"
                ].replace(tzinfo=None)
        df = pd.DataFrame(transactions)
        if df.empty:
            return Response(
                {"error": "No historical transaction data found for this product."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            validation_horizon_int = int(validation_horizon)
            if validation_horizon_int <= 0:
                return Response(
                    {"error": "Validation horizon must be a positive integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            backtest_results = backtest_prophet_forecast(
                product_sku, df.copy(), validation_horizon_int
            )
            if "error" in backtest_results:
                return Response(
                    {"error": backtest_results["error"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            metrics = backtest_results["metrics"]
            forecast_list = backtest_results["forecast"]
            product_details = {"name": product.name, "description": product.description}
            return Response(
                {
                    "product_details": product_details,
                    "metrics": metrics,
                    "forecast": forecast_list,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError:
            return Response(
                {"error": "Invalid validation_horizon. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as e:
        logger.exception(
            f"Prophet backtesting API error for SKU {product_sku}, horizon: {validation_horizon}. Error: {e}",
            exc_info=True,
        )
        return Response(
            {"error": f"Prophet backtesting failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "product_sku",
            OpenApiTypes.STR,
            OpenApiParameter.PATH,
            required=True,
            description="SKU of the product",
        ),
        OpenApiParameter(
            "validation_horizon",
            OpenApiTypes.INT,
            OpenApiParameter.PATH,
            required=True,
            description="Backtesting horizon in periods (e.g., days)",
        ),
        OpenApiParameter(
            "arima_order_str",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            required=False,
            description="Optional ARIMA order as p,d,q (e.g., '5,1,0')",
        ),
    ],
    responses={
        (200): {
            "type": "object",
            "properties": {
                "product_details": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
                "metrics": MetricsSchema,
                "forecast": {"type": "array", "items": ForecastItemSchema},
                "arima_order_used": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "example": [5, 1, 0],
                },
            },
        },
        (400): OpenApiTypes.OBJECT,
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Performs backtesting for ARIMA demand forecast and retrieves evaluation metrics.",
)
@api_view(["GET"])
def get_arima_backtesting(
    request, product_sku, validation_horizon, arima_order_str=None
):
    """Handles an API request to perform ARIMA-based backtesting on product demand forecasts and returns evaluation metrics.

    Args:
        request (HttpRequest): The HTTP request object.
        product_sku (str): The SKU identifier of the product to backtest.
        validation_horizon (str): The forecast validation horizon as a string representing a positive integer.
        arima_order_str (str, optional): Comma-separated ARIMA order parameters 'p,d,q' (e.g., '2,1,2'). Defaults to None, using (5,1,0).

    Returns:
        Response: A DRF Response containing product details, ARIMA forecast metrics, the forecast list, and the ARIMA order used.
                  Returns error responses with appropriate HTTP status codes if product not found, invalid input, no data, or processing errors occur.

    Logs detailed information about received parameters, data validation, and exceptions to aid debugging and monitoring."""
    logger.info(
        f"ARIMA Backtesting API: Request Received - SKU: {product_sku}, horizon_str: {validation_horizon}, order_str: {arima_order_str}"
    )
    logger.info(
        f"Value of validation_horizon at view entry: {validation_horizon}, Type: {type(validation_horizon)}"
    )
    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=404)
    queryset = Transaction.objects.filter(product__sku=product_sku).order_by(
        "transaction_date"
    )
    transactions = list(queryset.values("transaction_date", "quantity"))
    for transaction in transactions:
        if transaction["transaction_date"]:
            transaction["transaction_date"] = transaction["transaction_date"].replace(
                tzinfo=None
            )
    df = pd.DataFrame(transactions)
    if df.empty:
        return Response(
            {"error": "No historical transaction data found for this product."},
            status=404,
        )
    try:
        validation_horizon_int = int(validation_horizon)
        logger.info(
            f"Value of validation_horizon BEFORE int conversion: {validation_horizon}, Type: {type(validation_horizon)}"
        )
        if validation_horizon_int <= 0:
            return Response(
                {"error": "Validation horizon must be a positive integer."}, status=400
            )
        arima_order = 5, 1, 0
        if arima_order_str:
            try:
                p, d, q = map(int, arima_order_str.split(","))
                arima_order = p, d, q
            except ValueError:
                return Response(
                    {
                        "error": "Invalid arima_order format. Use 'p,d,q' (e.g., '2,1,2')."
                    },
                    status=400,
                )
        backtest_results = backtest_arima_forecast(
            product_sku, df, validation_horizon_int, arima_order=arima_order
        )
        if "error" in backtest_results:
            return Response({"error": backtest_results["error"]}, status=400)
        metrics = backtest_results["metrics"]
        forecast_list = backtest_results["forecast"]
        arima_order_used = backtest_results["arima_order_used"]
        product_details = {"name": product.name, "description": product.description}
        return Response(
            {
                "product_details": product_details,
                "metrics": metrics,
                "forecast": forecast_list,
                "arima_order_used": arima_order_used,
            }
        )
    except ValueError as ve:
        logger.error(
            f"ValueError during int(validation_horizon): Value: '{validation_horizon}', Error: {ve}",
            exc_info=True,
        )
        return Response(
            {"error": "Invalid validation_horizon. Must be an integer."}, status=400
        )
    except Exception as e:
        logger.error(
            f"ARIMA backtesting API error for SKU {product_sku}, horizon: {validation_horizon}, order: {arima_order}. Error: {e}",
            exc_info=True,
        )
        return Response({"error": f"ARIMA backtesting failed: {str(e)}"}, status=500)


@extend_schema(
    parameters=[
        OpenApiParameter(
            "product_sku",
            OpenApiTypes.STR,
            OpenApiParameter.PATH,
            required=False,
            description="Optional SKU to filter metrics for a specific product.",
        )
    ],
    responses={
        (200): {
            "type": "object",
            "properties": {
                "total_sales": {"type": "number", "format": "float"},
                "total_profit": {"type": "number", "format": "float"},
                "total_transactions": {"type": "integer"},
                "total_products": {"type": "integer"},
            },
            "example": {
                "total_sales": 12550.75,
                "total_profit": 3150.5,
                "total_transactions": 450,
                "total_products": 58,
            },
        },
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Retrieves dashboard metrics (Total Sales, Profit, Transactions, Products), optionally filtered by product SKU.",
)
@api_view(["GET"])
def get_dashboard_metrics(request, product_sku=None):
    """Retrieves dashboard metrics including total sales, total profit, total transactions, and total products,
    optionally filtered by a specific product SKU.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        product_sku (str, optional): SKU of the product to filter metrics by. If None, metrics are aggregated across all products.

    Returns:
        Response: A DRF Response object containing a JSON with keys 'total_sales', 'total_profit', 'total_transactions', and 'total_products'.
                  Returns a 404 response if the product SKU does not exist, or a 500 response on other errors."""
    try:
        transaction_queryset = Transaction.objects.filter(transaction_type="sale")
        if product_sku:
            try:
                product = Product.objects.get(sku=product_sku)
            except Product.DoesNotExist:
                return Response({"error": "Product not found."}, status=404)
            transaction_queryset = transaction_queryset.filter(product=product)
        total_sales = (
            transaction_queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        )
        total_revenue = (
            transaction_queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        )
        total_cost = (
            Transaction.objects.filter(transaction_type="purchase").aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )
        total_profit = total_revenue - total_cost
        total_transactions = transaction_queryset.count()
        total_products = Product.objects.count()
        metrics = {
            "total_sales": total_sales,
            "total_profit": total_profit,
            "total_transactions": total_transactions,
            "total_products": total_products,
        }
        return Response(metrics)
    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {e}", exc_info=True)
        return Response(
            {"error": f"Failed to calculate dashboard metrics: {str(e)}"}, status=500
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "product_sku",
            OpenApiTypes.STR,
            OpenApiParameter.PATH,
            required=False,
            description="Optional SKU to filter trend for a specific product.",
        )
    ],
    responses={
        (200): {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "format": "date"},
                    "total_sales": {"type": "number", "format": "float"},
                    "total_profit": {"type": "number", "format": "float"},
                },
            },
            "example": [
                {"month": "2024-01-01", "total_sales": 5000.0, "total_profit": 1200.5},
                {"month": "2024-02-01", "total_sales": 7550.75, "total_profit": 1950.0},
            ],
        },
        (404): OpenApiTypes.OBJECT,
        (500): OpenApiTypes.OBJECT,
    },
    description="Retrieves monthly sales and profit trend data, optionally filtered by product SKU.",
)
@api_view(["GET"])
def get_sales_profit_trend(request, product_sku=None):
    """Retrieve monthly sales and profit trend data for a specified product.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        product_sku (str, optional): SKU of the product to filter the sales and profit data. If None, aggregates data for all products.

    Returns:
        Response: A JSON response containing a list of dictionaries, each with keys:
            - 'month' (datetime): The month of the transactions.
            - 'total_sales' (Decimal): Total sales amount for the month.
            - 'total_profit' (Decimal): Calculated profit for the month (sales revenue minus cost).
        If the product SKU does not exist, returns a 404 error response.
        On failure, returns a 500 error response with an error message."""
    try:
        transaction_queryset = Transaction.objects.filter(transaction_type="sale")
        purchase_queryset = Transaction.objects.filter(transaction_type="purchase")
        if product_sku:
            try:
                product = Product.objects.get(sku=product_sku)
            except Product.DoesNotExist:
                return Response({"error": "Product not found."}, status=404)
            transaction_queryset = transaction_queryset.filter(product=product)
            purchase_queryset = purchase_queryset.filter(product=product)
        sales_profit_data = (
            transaction_queryset.annotate(month=TruncMonth("transaction_date"))
            .values("month")
            .annotate(
                total_sales=Sum("total_amount"),
                total_profit=Sum(
                    models.F("total_amount")
                    - models.F("unit_price") * models.F("quantity")
                ),
            )
            .order_by("month")
        )
        total_cost = (
            purchase_queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        )
        sales_profit_list = list(sales_profit_data)
        return Response(sales_profit_list)
    except Exception as e:
        logger.error(f"Error calculating sales and profit trend: {e}", exc_info=True)
        return Response(
            {"error": f"Failed to calculate sales and profit trend: {str(e)}"},
            status=500,
        )
