# products/forecast.py (Enhanced ARIMA Implementation)
from prophet import Prophet
import pandas as pd
import logging
from statsmodels.tsa.arima.model import ARIMA  # Import ARIMA
from statsmodels.tools.sm_exceptions import ValueWarning, HessianInversionWarning, ConvergenceWarning
import warnings
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

logger = logging.getLogger(__name__)


warnings.simplefilter('ignore', ValueWarning)
warnings.simplefilter('ignore', HessianInversionWarning)
warnings.simplefilter('ignore', ConvergenceWarning)


def forecast_demand_prophet(product_sku, historical_data, horizon):
    """Generates demand forecast using Prophet (as before)."""
    # ... (Prophet forecasting code - no changes needed) ...
    df = historical_data[['transaction_date', 'quantity']].rename(columns={'transaction_date': 'ds', 'quantity': 'y'})
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=horizon)
    forecast = model.predict(future)
    forecast = forecast[forecast['ds'] > df['ds'].max()]
    return forecast[['ds', 'yhat']]


def forecast_demand_arima(product_sku, historical_data, horizon, arima_order=(5, 1, 0)):
    """
    Generates a demand forecast for a product using ARIMA (Corrected - Daily Aggregation).
    """
    logger.info(f"Generating ARIMA forecast for product SKU: {product_sku}, horizon: {horizon}, ARIMA order: {arima_order}")

    df = historical_data[['transaction_date', 'quantity']].rename(columns={'transaction_date': 'ds', 'quantity': 'y'})

    # --- Explicit Daily Aggregation (Fix for Duplicate Dates) ---
    # Group by 'ds' (transaction_date) and sum 'y' (quantity) for each day
    daily_df = df.groupby(pd.Grouper(key='ds', freq='D')).sum().reset_index() # Group by day and sum
    ts = daily_df.set_index('ds')['y'].asfreq('D') # Now create daily TS
    ts = ts.fillna(method='ffill')

    logger.info(f"Time Series Data after Daily Aggregation - Shape: {ts.shape}, First 10 Dates: {ts.head(10).index.to_list()}") # Log shape and dates

    try:
        model = ARIMA(ts, order=arima_order)
        model_fit = model.fit()

        forecast_values = model_fit.forecast(steps=horizon)

        forecast_dates = pd.date_range(start=ts.index[-1], periods=horizon, freq='D')
        forecast_df = pd.DataFrame({'ds': forecast_dates, 'yhat': forecast_values.values})
        return forecast_df[['ds', 'yhat']]

    except Exception as e:
        logger.error(f"ARIMA Forecasting error for SKU {product_sku}: {e}", exc_info=True)
        raise e
def backtest_prophet_forecast(product_sku, historical_data, validation_horizon):
    """
    Performs backtesting for Prophet demand forecast and evaluates accuracy.
    (Corrected version - Forecasts for validation period)
    """
    logger.info(f"Starting Prophet backtesting for SKU: {product_sku}, validation_horizon: {validation_horizon}")

    df = historical_data[['transaction_date', 'quantity']].rename(columns={'transaction_date': 'ds', 'quantity': 'y'})
    daily_df = df.groupby(pd.Grouper(key='ds', freq='D')).sum().reset_index() # Group by day and sum
    ts = daily_df.set_index('ds')['y'].asfreq('D') # Now create daily TS
    ts = ts.fillna(method='ffill')

    # 1. Split Data into Training and Validation Sets
    train_df = df[:-validation_horizon]
    validation_df = df[-validation_horizon:]

    if train_df.empty or validation_df.empty:
        return {"error": "Insufficient data for backtesting. Need data for both training and validation periods."}

    # 2. Train Prophet Model on Training Data ONLY
    model = Prophet()
    model.fit(train_df)

    # 3. Create DataFrame for VALIDATION PERIOD Dates for Forecasting (Corrected)
    # Create a DataFrame with dates *only for the validation period* itself.
    validation_future = pd.DataFrame(validation_df['ds']) # Use validation_df 'ds' dates directly for future dataframe
    validation_forecast = model.predict(validation_future) # Predict only for validation dates

    # 4. Evaluate Forecast Accuracy (No changes needed)
    actual_values = validation_df['y'].values
    forecasted_values = validation_forecast['yhat'].values

    actual_values = actual_values[np.isfinite(forecasted_values)]
    forecasted_values = forecasted_values[np.isfinite(forecasted_values)]

    if not actual_values.size or not forecasted_values.size:
        metrics = {"mae": "NaN", "rmse": "NaN"}
    else:
        mae = mean_absolute_error(actual_values, forecasted_values)
        rmse = np.sqrt(mean_squared_error(actual_values, forecasted_values))
        metrics = {"mae": mae, "rmse": rmse}

    logger.info(f"Prophet backtesting completed... Metrics: MAE={mae:.2f}, RMSE={rmse:.2f}")

    # 5. Return Metrics and Validation Forecast
    return {"metrics": metrics, "forecast": validation_forecast[['ds', 'yhat']].to_dict('records')}

def backtest_arima_forecast(product_sku, historical_data, validation_horizon, arima_order=(5, 1, 0)):
    """
    Performs backtesting for ARIMA demand forecast and evaluates accuracy.

    Args:
        product_sku (str): Product SKU.
        historical_data (DataFrame): DataFrame with 'ds' and 'y' columns.
        validation_horizon (int): Length of the validation period (number of days).
        arima_order (tuple, optional): ARIMA model order (p, d, q). Defaults to (5, 1, 0).

    Returns:
        dict: Dictionary containing evaluation metrics (MAE, RMSE, etc.) and the forecast DataFrame for the validation period.
    """
    logger.info(f"Starting ARIMA backtesting for SKU: {product_sku}, validation_horizon: {validation_horizon}, ARIMA order: {arima_order}")

    df = historical_data[['transaction_date', 'quantity']].rename(columns={'transaction_date': 'ds', 'quantity': 'y'})
    # Group by 'ds' (transaction_date) and sum 'y' (quantity) for each day
    df = df.groupby(pd.Grouper(key='ds', freq='D')).sum().reset_index() # Group by day and sum

    # 1. Split Data into Training and Validation Sets
    train_df = df[:-validation_horizon]
    validation_df = df[-validation_horizon:]

    if train_df.empty or validation_df.empty:
        return {"error": "Insufficient data for backtesting. Need data for both training and validation periods."}

    # 2. Train ARIMA Model on Training Data ONLY
    ts_train = train_df.set_index('ds')['y'] # Daily TS for training # REMOVE asfreq

    model = ARIMA(ts_train, order=arima_order) #Define model before the block
    try:
        model_fit = model.fit()

        # 3. Generate Forecast for Validation Period
        validation_dates = validation_df['ds'] # Dates for validation period
        start_date = validation_dates.iloc[0] # Start date of validation period
        end_date = validation_dates.iloc[-1]  # End date of validation period
        forecast_values = model_fit.predict(start=start_date, end=end_date) # Forecast for validation dates
        validation_forecast_df = pd.DataFrame({'ds': validation_dates, 'yhat': forecast_values}) # Create forecast DF

        # 4. Evaluate Forecast Accuracy
        actual_values = validation_df['y'].values
        forecasted_values = validation_forecast_df['yhat'].values

        actual_values = actual_values[np.isfinite(forecasted_values)]
        forecasted_values = forecasted_values[np.isfinite(forecasted_values)]

        if not actual_values.size or not forecasted_values.size:
            metrics = {"mae": "NaN", "rmse": "NaN"}
        else:
            mae = mean_absolute_error(actual_values, forecasted_values)
            rmse = np.sqrt(mean_squared_error(actual_values, forecasted_values))
            metrics = {"mae": mae, "rmse": rmse}

        logger.info(f"ARIMA backtesting completed... Metrics: MAE={mae:.2f}, RMSE={rmse:.2f}, ARIMA order: {arima_order}") # Log ARIMA order

        # 5. Return Metrics and Validation Forecast
        return {"metrics": metrics, "forecast": validation_forecast_df[['ds', 'yhat']].to_dict('records'), "arima_order_used": arima_order} # Return arima_order_used

    except Exception as e:
        logger.error(f"ARIMA Forecasting error for SKU {product_sku}: {e}", exc_info=True)
        # We must include the error dictionary, or a valid dictionary
        return {"error": f"ARIMA forecasting failed: {str(e)}", "metrics": {"mae": "NaN", "rmse": "NaN"}, "forecast": []} #Return the error dictionary