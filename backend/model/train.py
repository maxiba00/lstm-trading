"""
LSTM model training.
One model per ticker, saved to models/<TICKER>.keras.
Architecture mirrors the thesis: LSTM(50) → Dropout → Dense(1).
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping

from data.fetcher import build_feature_dataframe

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def create_sequences(data: np.ndarray, step_size: int) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(len(data) - step_size):
        X.append(data[i : i + step_size])
        y.append(data[i + step_size, 0])  # predict Close (column 0)
    return np.array(X), np.array(y)


def build_model(step_size: int, n_features: int, lstm_units: int = 50, dropout: float = 0.3) -> Sequential:
    model = Sequential([
        Input(shape=(step_size, n_features)),
        LSTM(lstm_units, activation="tanh"),
        Dropout(dropout),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def train_ticker(
    ticker: str,
    start: str = "2014-01-01",
    end: str = "2024-12-31",
    step_size: int = 60,
    train_ratio: float = 0.7,
    epochs: int = 100,
    batch_size: int = 32,
    lstm_units: int = 50,
    dropout: float = 0.3,
    include_wiki: bool = True,
    include_trends: bool = True,
    include_sentiment: bool = True,
) -> Optional[dict]:
    """
    Train LSTM for one ticker. Returns metrics dict or None on failure.
    Saves model + scaler to models/<TICKER>.keras / models/<TICKER>_scaler.pkl
    """
    logger.info(f"Training {ticker}...")

    df = build_feature_dataframe(
        ticker, start, end,
        include_wiki=include_wiki,
        include_trends=include_trends,
        include_sentiment=include_sentiment,
    )
    if df is None or len(df) < step_size + 10:
        logger.error(f"Insufficient data for {ticker}")
        return None

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(df.values)

    train_size = int(len(scaled) * train_ratio)
    train_data = scaled[:train_size]
    test_data = scaled[train_size:]

    X_train, y_train = create_sequences(train_data, step_size)
    X_test, y_test = create_sequences(test_data, step_size)

    if len(X_train) == 0 or len(X_test) == 0:
        logger.error(f"Not enough sequences for {ticker}")
        return None

    n_features = X_train.shape[2]
    model = build_model(step_size, n_features, lstm_units, dropout)

    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)

    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_test, y_test),
        callbacks=[early_stop],
        verbose=0,
    )

    # Evaluate
    mse = float(model.evaluate(X_test, y_test, verbose=0))
    rmse = float(np.sqrt(mse))

    # Inverse-transform predictions for directional accuracy
    preds_scaled = model.predict(X_test, verbose=0)
    pad = np.zeros((len(preds_scaled), n_features - 1))
    preds = scaler.inverse_transform(np.hstack([preds_scaled, pad]))[:, 0]
    actual = scaler.inverse_transform(np.hstack([y_test.reshape(-1, 1), pad]))[:, 0]

    # Directional accuracy: did predicted next-day price move in the right direction?
    pred_dir = np.sign(preds[1:] - actual[:-1])
    actual_dir = np.sign(actual[1:] - actual[:-1])
    dir_accuracy = float(np.mean(pred_dir == actual_dir))

    # Save model and scaler
    model_path = MODELS_DIR / f"{ticker}.keras"
    scaler_path = MODELS_DIR / f"{ticker}_scaler.pkl"
    model.save(str(model_path))
    joblib.dump(scaler, str(scaler_path))

    # Save feature column names for inference
    cols_path = MODELS_DIR / f"{ticker}_columns.txt"
    cols_path.write_text("\n".join(df.columns.tolist()))

    metrics = {
        "ticker": ticker,
        "mse": mse,
        "rmse": rmse,
        "directional_accuracy": dir_accuracy,
        "n_features": n_features,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "epochs_run": len(history.history["loss"]),
    }
    logger.info(f"{ticker} trained — RMSE: {rmse:.4f}, Dir.Acc: {dir_accuracy:.2%}")
    return metrics


def train_all(tickers: list, **kwargs) -> list:
    results = []
    for ticker in tickers:
        result = train_ticker(ticker, **kwargs)
        if result:
            results.append(result)
    return results
