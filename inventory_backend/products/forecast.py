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
    """Generates demand forecast using Prophet."""
    try: # Added try-except block

        # 1. Data Preparation
        df = historical_data[['transaction_date', 'quantity']].rename(
            columns={'transaction_date': 'ds', 'quantity': 'y'})

        # Ensure 'ds' is datetime
        df['ds'] = pd.to_datetime(df['ds'])

        # Aggregate duplicate dates (SUM quantities for the same day) - CRUCIAL STEP
        df = df.groupby('ds')['y'].sum().reset_index()

        # Sort by date
        df = df.sort_values('ds')

        # 2. Train Prophet Model
        model = Prophet()
        model.fit(df)

        # 3. Make Future DataFrame
        future = model.make_future_dataframe(periods=horizon)

        # 4. Forecast
        forecast = model.predict(future)

        # 5. Return Only Future Forecast Dates
        forecast = forecast[forecast['ds'] > df['ds'].max()]

        # 6. Ensure it is always returned as list
        return forecast[['ds', 'yhat']].to_dict('records')

    except Exception as e: # Catch any errors
        logger.error(f"Prophet forecasting failed for SKU: {product_sku}. Error: {e}", exc_info=True)
        return []  # Return an empty list as JSON is best if there is an error.


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
    logger.info(f"Starting Prophet backtesting for SKU: {product_sku}, validation_horizon: {validation_horizon}")

    # 1. Data Preparation
    df = historical_data[['transaction_date', 'quantity']].rename(columns={'transaction_date': 'ds', 'quantity': 'y'})

    # Ensure 'ds' is datetime
    df['ds'] = pd.to_datetime(df['ds'])

    # Aggregate duplicate dates (SUM quantities for the same day) - CRUCIAL STEP
    df = df.groupby('ds')['y'].sum().reset_index()

    # Sort by date
    df = df.sort_values('ds')

    # 2. Split Data into Training and Validation Sets
    train_df = df[:-validation_horizon]
    validation_df = df[-validation_horizon:]

    print(f"train_df head:\n{train_df.head()}")  # Inspect the training data
    print(f"validation_df head:\n{validation_df.head()}")  # Inspect the validation data
    print(f"train_df tail:\n{train_df.tail()}")  # Inspect the tail of the training data
    print(f"validation_df tail:\n{validation_df.tail()}")  # Inspect the tail of the validation data

    if train_df.empty or validation_df.empty:
        return {"error": "Insufficient data for backtesting. Need data for both training and validation periods."}

    # 3. Train Prophet Model on Training Data ONLY
    model = Prophet()
    try:
        model.fit(train_df)
    except Exception as e:
        logger.error(f"Prophet model.fit() failed: {e}", exc_info=True)
        return {"error": f"Prophet model fitting failed: {str(e)}"}

    # 4. Create DataFrame for VALIDATION PERIOD Dates for Forecasting (Corrected)
    validation_future = pd.DataFrame({'ds': validation_df['ds']})
    try:
        validation_forecast = model.predict(validation_future)
    except Exception as e:
        logger.error(f"Prophet model.predict() failed: {e}", exc_info=True)
        return {"error": f"Prophet model prediction failed: {str(e)}"}

    print(f"validation_forecast head:\n{validation_forecast.head()}") #Inspect the validation forecast

    # 5. Evaluate Forecast Accuracy
    actual_values = validation_df['y'].values
    forecasted_values = validation_forecast['yhat'].values

    # Handle NaN values, which Prophet can sometimes produce.
    actual_values = actual_values[np.isfinite(forecasted_values)]
    forecasted_values = forecasted_values[np.isfinite(forecasted_values)]

    if not actual_values.size or not forecasted_values.size:
        metrics = {"mae": "NaN", "rmse": "NaN"}
    else:
        mae = mean_absolute_error(actual_values, forecasted_values)
        rmse = np.sqrt(mean_squared_error(actual_values, forecasted_values))
        metrics = {"mae": mae, "rmse": rmse}

    logger.info(f"Prophet backtesting completed... Metrics: MAE={mae:.2f}, RMSE={rmse:.2f}")

    # 6. Return Metrics and Validation Forecast
    return {"metrics": metrics, "forecast": validation_forecast[['ds', 'yhat']].to_dict('records')}
def backtest_arima_forecast(product_sku, historical_data, validation_horizon, arima_order=(0, 0, 0)):
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
    daily_df = df.groupby(pd.Grouper(key='ds', freq='D')).sum().reset_index() # Group by day and sum
    daily_df['ds'] = pd.to_datetime(daily_df['ds']) #Ensure that the ds is in datetime

    ts = daily_df.set_index('ds')['y'] # Now create daily TS # REMOVE asfreq

    # 1. Split Data into Training and Validation Sets
    train_ts = ts[:-validation_horizon]  # Training data time series
    validation_ts = ts[-validation_horizon:] # Validation data time series

    if train_ts.empty or validation_ts.empty:
        return {"error": "Insufficient data for backtesting. Need data for both training and validation periods."}

    # 2. Train ARIMA Model on Training Data ONLY
    model = ARIMA(train_ts, order=arima_order) #Use train_ts
    try:
        model_fit = model.fit()

        # 3. Generate Forecast for Validation Period
        forecast_values = model_fit.predict(start=validation_ts.index.min(), end=validation_ts.index.max()) # Forecast for validation dates

        # Create a validation forecast dataframe with the same index
        validation_forecast_df = pd.DataFrame({'ds': validation_ts.index, 'yhat': forecast_values}) # Create forecast DF

        # 4. Evaluate Forecast Accuracy
        actual_values = validation_ts.values #Use the ts_validation
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
        return {"error": f"ARIMA forecasting failed: {str(e)}", "metrics": {"mae": "NaN", "rmse": "NaN"}, "forecast": []} #Return the error dictionary