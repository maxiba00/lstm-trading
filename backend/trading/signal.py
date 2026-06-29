"""
Signal generation: converts raw predictions into LONG / SHORT / HOLD signals
based on configurable thresholds.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Signal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    ticker: str
    signal: Signal
    current_price: float
    predicted_price: float
    predicted_return_pct: float
    confidence: float
    mc_std: float
    reason: str


def generate_signal(
    prediction: dict,
    min_return_pct: float = 1.0,      # |predicted return| must exceed this
    min_confidence: float = 0.60,      # MC Dropout confidence must exceed this
    allow_short: bool = True,
) -> TradingSignal:
    """
    Apply threshold rules to a prediction dict (from predict.predict_next_day).

    Signal logic:
      LONG  if predicted_return_pct >  +min_return_pct AND confidence >= min_confidence
      SHORT if predicted_return_pct < -min_return_pct AND confidence >= min_confidence AND allow_short
      HOLD  otherwise
    """
    ticker = prediction["ticker"]
    ret = prediction["predicted_return_pct"]
    conf = prediction["confidence"]
    cp = prediction["current_price"]
    pp = prediction["predicted_price"]
    std = prediction["mc_std"]

    if conf < min_confidence:
        return TradingSignal(
            ticker=ticker, signal=Signal.HOLD,
            current_price=cp, predicted_price=pp,
            predicted_return_pct=ret, confidence=conf, mc_std=std,
            reason=f"Low confidence ({conf:.0%} < {min_confidence:.0%})",
        )

    if ret > min_return_pct:
        return TradingSignal(
            ticker=ticker, signal=Signal.LONG,
            current_price=cp, predicted_price=pp,
            predicted_return_pct=ret, confidence=conf, mc_std=std,
            reason=f"Predicted +{ret:.2f}% with {conf:.0%} confidence",
        )

    if allow_short and ret < -min_return_pct:
        return TradingSignal(
            ticker=ticker, signal=Signal.SHORT,
            current_price=cp, predicted_price=pp,
            predicted_return_pct=ret, confidence=conf, mc_std=std,
            reason=f"Predicted {ret:.2f}% with {conf:.0%} confidence",
        )

    return TradingSignal(
        ticker=ticker, signal=Signal.HOLD,
        current_price=cp, predicted_price=pp,
        predicted_return_pct=ret, confidence=conf, mc_std=std,
        reason=f"Predicted return {ret:.2f}% below threshold ±{min_return_pct:.1f}%",
    )


def generate_signals(
    predictions: list,
    min_return_pct: float = 1.0,
    min_confidence: float = 0.60,
    allow_short: bool = True,
) -> list[TradingSignal]:
    return [
        generate_signal(p, min_return_pct, min_confidence, allow_short)
        for p in predictions
    ]
