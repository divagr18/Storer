from prophet import Prophet
import pandas as pd
import logging
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tools.sm_exceptions import (
    ValueWarning,
    HessianInversionWarning,
    ConvergenceWarning,
)
import warnings
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

logger = logging.getLogger(__name__)
warnings.simplefilter("ignore", ValueWarning)
warnings.simplefilter("ignore", HessianInversionWarning)
warnings.simplefilter("ignore", ConvergenceWarning)


def forecast_demand_prophet(product_sku, historical_data, horizon):
    """Generates a demand forecast for a given product using Facebook Prophet.

    Args:
        product_sku (str): The SKU identifier for the product being forecasted.
        historical_data (pandas.DataFrame): DataFrame containing historical sales data with
            columns 'transaction_date' (date of transaction) and 'quantity' (units sold).
        horizon (int): Number of future periods (days) to forecast demand for.

    Returns:
        list of dict: A list of dictionaries each containing 'ds' (forecast date as Timestamp)
            and 'yhat' (predicted demand) for the forecast horizon. Returns an empty list if
            forecasting fails.

    Logs an error if the forecasting process encounters an exception."""
    try:
        df = historical_data[["transaction_date", "quantity"]].rename(
            columns={"transaction_date": "ds", "quantity": "y"}
        )
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.groupby("ds")["y"].sum().reset_index()
        df = df.sort_values("ds")
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon)
        forecast = model.predict(future)
        forecast = forecast[forecast["ds"] > df["ds"].max()]
        return forecast[["ds", "yhat"]].to_dict("records")
    except Exception as e:
        logger.error(
            f"Prophet forecasting failed for SKU: {product_sku}. Error: {e}",
            exc_info=True,
        )
        return []


def forecast_demand_arima(product_sku, historical_data, horizon, arima_order=(5, 1, 0)):
    """Generates a daily demand forecast for a product SKU using an ARIMA time series model.

    Aggregates historical transaction data by day to handle duplicate transaction dates, fits an ARIMA model to the aggregated time series, and forecasts demand over a given horizon.

    Args:
        product_sku (str): The SKU identifier for the product to forecast.
        historical_data (pandas.DataFrame): Historical transaction data containing at least 'transaction_date' and 'quantity' columns.
        horizon (int): Number of future days to forecast.
        arima_order (tuple of int, optional): The (p, d, q) order parameters for the ARIMA model. Defaults to (5, 1, 0).

    Returns:
        pandas.DataFrame: A DataFrame with two columns: 'ds' (forecast dates) and 'yhat' (forecasted demand values).

    Raises:
        Exception: Propagates any exceptions encountered during model fitting or forecasting."""
    logger.info(
        f"Generating ARIMA forecast for product SKU: {product_sku}, horizon: {horizon}, ARIMA order: {arima_order}"
    )
    df = historical_data[["transaction_date", "quantity"]].rename(
        columns={"transaction_date": "ds", "quantity": "y"}
    )
    daily_df = df.groupby(pd.Grouper(key="ds", freq="D")).sum().reset_index()
    ts = daily_df.set_index("ds")["y"].asfreq("D")
    ts = ts.fillna(method="ffill")
    logger.info(
        f"Time Series Data after Daily Aggregation - Shape: {ts.shape}, First 10 Dates: {ts.head(10).index.to_list()}"
    )
    try:
        model = ARIMA(ts, order=arima_order)
        model_fit = model.fit()
        forecast_values = model_fit.forecast(steps=horizon)
        forecast_dates = pd.date_range(start=ts.index[-1], periods=horizon, freq="D")
        forecast_df = pd.DataFrame(
            {"ds": forecast_dates, "yhat": forecast_values.values}
        )
        return forecast_df[["ds", "yhat"]]
    except Exception as e:
        logger.error(
            f"ARIMA Forecasting error for SKU {product_sku}: {e}", exc_info=True
        )
        raise e


def backtest_prophet_forecast(product_sku, historical_data, validation_horizon):
    """Backtests a Prophet time series forecasting model on historical product sales data.

    Args:
        product_sku (str): The SKU identifier of the product being forecasted.
        historical_data (pd.DataFrame): Historical sales data containing 'transaction_date' and 'quantity' columns.
        validation_horizon (int): Number of most recent days reserved for validation/testing.

    Returns:
        dict: A dictionary with either:
            - 'metrics': A dict containing forecast accuracy metrics 'mae' (mean absolute error) and 'rmse' (root mean squared error),
              and 'forecast': a list of dicts with predicted dates ('ds') and forecasted values ('yhat') for the validation period.
            - 'error': A string describing the failure reason if backtesting cannot be performed (e.g., insufficient data or model errors).

    This function prepares and aggregates the data, trains a Prophet model on the training subset,
    forecasts over the validation horizon, and evaluates forecast accuracy. Logs key steps and errors for monitoring and debugging."""
    logger.info(
        f"Starting Prophet backtesting for SKU: {product_sku}, validation_horizon: {validation_horizon}"
    )
    df = historical_data[["transaction_date", "quantity"]].rename(
        columns={"transaction_date": "ds", "quantity": "y"}
    )
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.groupby("ds")["y"].sum().reset_index()
    df = df.sort_values("ds")
    train_df = df[:-validation_horizon]
    validation_df = df[-validation_horizon:]
    print(f"train_df head:\n{train_df.head()}")
    print(f"validation_df head:\n{validation_df.head()}")
    print(f"train_df tail:\n{train_df.tail()}")
    print(f"validation_df tail:\n{validation_df.tail()}")
    if train_df.empty or validation_df.empty:
        return {
            "error": "Insufficient data for backtesting. Need data for both training and validation periods."
        }
    model = Prophet()
    try:
        model.fit(train_df)
    except Exception as e:
        logger.error(f"Prophet model.fit() failed: {e}", exc_info=True)
        return {"error": f"Prophet model fitting failed: {str(e)}"}
    validation_future = pd.DataFrame({"ds": validation_df["ds"]})
    try:
        validation_forecast = model.predict(validation_future)
    except Exception as e:
        logger.error(f"Prophet model.predict() failed: {e}", exc_info=True)
        return {"error": f"Prophet model prediction failed: {str(e)}"}
    print(f"validation_forecast head:\n{validation_forecast.head()}")
    actual_values = validation_df["y"].values
    forecasted_values = validation_forecast["yhat"].values
    actual_values = actual_values[np.isfinite(forecasted_values)]
    forecasted_values = forecasted_values[np.isfinite(forecasted_values)]
    if not actual_values.size or not forecasted_values.size:
        metrics = {"mae": "NaN", "rmse": "NaN"}
    else:
        mae = mean_absolute_error(actual_values, forecasted_values)
        rmse = np.sqrt(mean_squared_error(actual_values, forecasted_values))
        metrics = {"mae": mae, "rmse": rmse}
    logger.info(
        f"Prophet backtesting completed... Metrics: MAE={mae:.2f}, RMSE={rmse:.2f}"
    )
    return {
        "metrics": metrics,
        "forecast": validation_forecast[["ds", "yhat"]].to_dict("records"),
    }


def backtest_arima_forecast(
    product_sku, historical_data, validation_horizon, arima_order=(0, 0, 0)
):
    """Backtests an ARIMA model for demand forecasting on historical product sales data and evaluates forecast accuracy.

    Args:
        product_sku (str): The SKU identifier of the product.
        historical_data (pandas.DataFrame): Historical sales data containing at least 'transaction_date' and 'quantity' columns.
        validation_horizon (int): Number of most recent days to reserve as the validation period.
        arima_order (tuple of int, optional): The (p, d, q) order parameters for the ARIMA model. Defaults to (0, 0, 0).

    Returns:
        dict: A dictionary containing:
            - 'metrics' (dict): Forecast evaluation metrics, including 'mae' and 'rmse', or "NaN" if evaluation failed.
            - 'forecast' (list of dict): List of forecasted values for the validation period with keys 'ds' (date) and 'yhat' (forecast).
            - 'arima_order_used' (tuple): The ARIMA order parameters used for the model.
          If an error occurs or insufficient data is provided, returns a dictionary with an 'error' message and fallback metrics."""
    logger.info(
        f"Starting ARIMA backtesting for SKU: {product_sku}, validation_horizon: {validation_horizon}, ARIMA order: {arima_order}"
    )
    df = historical_data[["transaction_date", "quantity"]].rename(
        columns={"transaction_date": "ds", "quantity": "y"}
    )
    daily_df = df.groupby(pd.Grouper(key="ds", freq="D")).sum().reset_index()
    daily_df["ds"] = pd.to_datetime(daily_df["ds"])
    ts = daily_df.set_index("ds")["y"]
    train_ts = ts[:-validation_horizon]
    validation_ts = ts[-validation_horizon:]
    if train_ts.empty or validation_ts.empty:
        return {
            "error": "Insufficient data for backtesting. Need data for both training and validation periods."
        }
    model = ARIMA(train_ts, order=arima_order)
    try:
        model_fit = model.fit()
        forecast_values = model_fit.predict(
            start=validation_ts.index.min(), end=validation_ts.index.max()
        )
        validation_forecast_df = pd.DataFrame(
            {"ds": validation_ts.index, "yhat": forecast_values}
        )
        actual_values = validation_ts.values
        forecasted_values = validation_forecast_df["yhat"].values
        actual_values = actual_values[np.isfinite(forecasted_values)]
        forecasted_values = forecasted_values[np.isfinite(forecasted_values)]
        if not actual_values.size or not forecasted_values.size:
            metrics = {"mae": "NaN", "rmse": "NaN"}
        else:
            mae = mean_absolute_error(actual_values, forecasted_values)
            rmse = np.sqrt(mean_squared_error(actual_values, forecasted_values))
            metrics = {"mae": mae, "rmse": rmse}
        logger.info(
            f"ARIMA backtesting completed... Metrics: MAE={mae:.2f}, RMSE={rmse:.2f}, ARIMA order: {arima_order}"
        )
        return {
            "metrics": metrics,
            "forecast": validation_forecast_df[["ds", "yhat"]].to_dict("records"),
            "arima_order_used": arima_order,
        }
    except Exception as e:
        logger.error(
            f"ARIMA Forecasting error for SKU {product_sku}: {e}", exc_info=True
        )
        return {
            "error": f"ARIMA forecasting failed: {str(e)}",
            "metrics": {"mae": "NaN", "rmse": "NaN"},
            "forecast": [],
        }
