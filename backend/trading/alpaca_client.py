"""
Alpaca paper trading client.
All orders are placed on the paper trading endpoint — no real money involved.
Set ALPACA_API_KEY + ALPACA_SECRET_KEY in environment.
"""

import os
import logging
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

logger = logging.getLogger(__name__)

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
PAPER = True  # always paper trading


def _get_client() -> TradingClient:
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=PAPER)


def get_account() -> dict:
    client = _get_client()
    acct = client.get_account()
    return {
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "portfolio_value": float(acct.portfolio_value),
        "buying_power": float(acct.buying_power),
        "pnl": float(acct.equity) - float(acct.last_equity),
    }


def get_positions() -> list:
    client = _get_client()
    positions = client.get_all_positions()
    return [
        {
            "ticker": p.symbol,
            "qty": float(p.qty),
            "side": "long" if float(p.qty) > 0 else "short",
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc) * 100,
        }
        for p in positions
    ]


def place_order(
    ticker: str,
    side: str,          # "buy" or "sell"
    notional: float,    # dollar amount to invest
    stop_loss_pct: Optional[float] = None,
) -> Optional[dict]:
    """Place a market order for `notional` dollars of `ticker`."""
    client = _get_client()
    order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

    try:
        req = MarketOrderRequest(
            symbol=ticker,
            notional=round(notional, 2),
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = client.submit_order(req)
        logger.info(f"Order placed: {side} {ticker} ${notional:.2f} → {order.id}")
        return {
            "order_id": str(order.id),
            "ticker": ticker,
            "side": side,
            "notional": notional,
            "status": str(order.status),
        }
    except Exception as e:
        logger.error(f"Order failed for {ticker}: {e}")
        return None


def close_position(ticker: str) -> Optional[dict]:
    """Close entire position for ticker."""
    client = _get_client()
    try:
        resp = client.close_position(ticker)
        return {"ticker": ticker, "closed": True, "order_id": str(resp.id)}
    except Exception as e:
        logger.error(f"Close position failed for {ticker}: {e}")
        return None


def get_recent_orders(limit: int = 50) -> list:
    client = _get_client()
    req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
    orders = client.get_orders(req)
    return [
        {
            "order_id": str(o.id),
            "ticker": o.symbol,
            "side": str(o.side),
            "qty": float(o.qty or 0),
            "notional": float(o.notional or 0),
            "status": str(o.status),
            "filled_avg_price": float(o.filled_avg_price or 0),
            "created_at": str(o.created_at),
            "filled_at": str(o.filled_at) if o.filled_at else None,
        }
        for o in orders
    ]
