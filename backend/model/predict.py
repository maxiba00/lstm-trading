"""
Inference with Monte Carlo Dropout for confidence estimation.
Runs N forward passes with dropout active → mean = prediction, std = uncertainty.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import joblib
import tensorflow as tf
from tensorflow.keras.models import load_model

from data.fetcher import build_feature_dataframe

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"
STEP_SIZE = 60
MC_SAMPLES = 50  # forward passes for confidence estimation


def _load_model_and_scaler(ticker: str):
    model_path = MODELS_DIR / f"{ticker}.keras"
    scaler_path = MODELS_DIR / f"{ticker}_scaler.pkl"
    cols_path = MODELS_DIR / f"{ticker}_columns.txt"

    if not model_path.exists() or not scaler_path.exists():
        return None, None, None

    model = load_model(str(model_path))
    scaler = joblib.load(str(scaler_path))
    columns = cols_path.read_text().strip().split("\n") if cols_path.exists() else None
    return model, scaler, columns


def predict_next_day(
    ticker: str,
    lookback_days: int = 90,
    mc_samples: int = MC_SAMPLES,
) -> Optional[dict]:
    """
    Predict next-day close price for ticker using the last `lookback_days` of data.

    Returns:
        {
            ticker, current_price, predicted_price, predicted_return_pct,
            confidence (0-1, based on MC Dropout std), mc_std, signal_raw
        }
    """
    from datetime import datetime, timedelta

    model, scaler, columns = _load_model_and_scaler(ticker)
    if model is None:
        logger.error(f"No trained model found for {ticker}")
        return None

    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=lookback_days + 30)).strftime("%Y-%m-%d")

    df = build_feature_dataframe(ticker, start, end)
    if df is None or len(df) < STEP_SIZE:
        logger.error(f"Not enough data for inference: {ticker}")
        return None

    # Align columns to training feature order
    if columns:
        for col in columns:
            if col not in df.columns:
                df[col] = 0.0
        df = df[columns]

    scaled = scaler.transform(df.values)
    sequence = scaled[-STEP_SIZE:]  # last 60 days
    X = sequence.reshape(1, STEP_SIZE, scaled.shape[1])

    # Monte Carlo Dropout: run N times with training=True to keep dropout active
    mc_preds = []
    for _ in range(mc_samples):
        pred = model(X, training=True).numpy()[0][0]
        mc_preds.append(pred)

    mc_preds = np.array(mc_preds)
    pred_scaled_mean = mc_preds.mean()
    pred_scaled_std = mc_preds.std()

    # Inverse-transform
    n_features = scaled.shape[1]
    pad = np.zeros(n_features - 1)

    predicted_price = scaler.inverse_transform(
        np.array([[pred_scaled_mean] + list(pad)])
    )[0][0]

    current_price = float(df["Close"].iloc[-1])
    predicted_return_pct = (predicted_price - current_price) / current_price * 100

    # Confidence: inverse of normalized std (lower std → higher confidence)
    # Clamp to [0, 1]
    confidence = float(max(0.0, min(1.0, 1.0 - (pred_scaled_std * 10))))

    return {
        "ticker": ticker,
        "current_price": round(current_price, 4),
        "predicted_price": round(float(predicted_price), 4),
        "predicted_return_pct": round(predicted_return_pct, 4),
        "confidence": round(confidence, 4),
        "mc_std": round(float(pred_scaled_std), 6),
        "n_features": n_features,
    }


def batch_predict(tickers: list, **kwargs) -> list:
    results = []
    for ticker in tickers:
        result = predict_next_day(ticker, **kwargs)
        if result:
            results.append(result)
    return results
