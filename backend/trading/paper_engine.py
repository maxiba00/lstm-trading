"""
Internal paper trading engine.
Echte Marktpreise via yfinance, Positionen/Orders in PostgreSQL.
Gleiche API-Schnittstelle wie alpaca_client.py — einfach später austauschbar.
"""

import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
from sqlalchemy.orm import Session

from db.models import PaperOrder, PaperPosition, PaperAccount

logger = logging.getLogger(__name__)

STARTING_CASH = 100_000.0  # virtuelles Startkapital


def _get_or_create_account(db: Session) -> PaperAccount:
    acct = db.query(PaperAccount).filter(PaperAccount.id == 1).first()
    if not acct:
        acct = PaperAccount(id=1, cash=STARTING_CASH, starting_cash=STARTING_CASH)
        db.add(acct)
        db.commit()
        db.refresh(acct)
    return acct


def _current_price(ticker: str) -> Optional[float]:
    try:
        data = yf.download(ticker, period="1d", progress=False, auto_adjust=True)
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"Price fetch failed for {ticker}: {e}")
        return None


def get_account(db: Session) -> dict:
    acct = _get_or_create_account(db)
    positions = db.query(PaperPosition).filter(PaperPosition.qty != 0).all()

    # Berechne unrealisiertes P&L über alle Positionen
    portfolio_value = acct.cash
    for pos in positions:
        price = _current_price(pos.ticker)
        if price:
            portfolio_value += pos.qty * price

    pnl = portfolio_value - acct.starting_cash

    return {
        "equity": round(portfolio_value, 2),
        "cash": round(acct.cash, 2),
        "portfolio_value": round(portfolio_value, 2),
        "buying_power": round(acct.cash, 2),
        "pnl": round(pnl, 2),
        "starting_cash": round(acct.starting_cash, 2),
    }


def get_positions(db: Session) -> list:
    positions = db.query(PaperPosition).filter(PaperPosition.qty != 0).all()
    result = []
    for pos in positions:
        price = _current_price(pos.ticker) or pos.avg_entry_price
        market_value = pos.qty * price
        unrealized_pl = (price - pos.avg_entry_price) * pos.qty
        unrealized_plpc = (price - pos.avg_entry_price) / pos.avg_entry_price * 100
        result.append({
            "ticker": pos.ticker,
            "qty": pos.qty,
            "side": "long" if pos.qty > 0 else "short",
            "avg_entry": round(pos.avg_entry_price, 4),
            "current_price": round(price, 4),
            "market_value": round(market_value, 2),
            "unrealized_pl": round(unrealized_pl, 2),
            "unrealized_plpc": round(unrealized_plpc, 2),
        })
    return result


def place_order(
    ticker: str,
    side: str,
    notional: float,
    db: Session,
    signal_id: Optional[int] = None,
) -> Optional[dict]:
    """
    Simuliert eine Market-Order zum aktuellen Marktpreis.
    side: 'buy' oder 'sell'
    notional: Dollar-Betrag
    """
    price = _current_price(ticker)
    if not price:
        logger.error(f"Cannot place order for {ticker}: no price available")
        return None

    acct = _get_or_create_account(db)
    qty = notional / price

    if side == "buy":
        if acct.cash < notional:
            logger.warning(f"Insufficient cash for {ticker}: need ${notional:.2f}, have ${acct.cash:.2f}")
            return None
        acct.cash -= notional
        # Bestehende Position updaten oder neu anlegen
        pos = db.query(PaperPosition).filter(PaperPosition.ticker == ticker).first()
        if pos:
            # Durchschnittlicher Einstiegspreis
            total_qty = pos.qty + qty
            pos.avg_entry_price = (pos.qty * pos.avg_entry_price + qty * price) / total_qty
            pos.qty = total_qty
        else:
            pos = PaperPosition(ticker=ticker, qty=qty, avg_entry_price=price)
            db.add(pos)

    elif side == "sell":
        pos = db.query(PaperPosition).filter(PaperPosition.ticker == ticker).first()
        if not pos or pos.qty < qty:
            # Short selling: neue Short-Position
            pos = pos or PaperPosition(ticker=ticker, qty=0, avg_entry_price=price)
            if pos not in db:
                db.add(pos)
            pos.qty -= qty
            pos.avg_entry_price = price
        else:
            pos.qty -= qty
        acct.cash += notional

    order = PaperOrder(
        ticker=ticker,
        side=side,
        notional=notional,
        qty=qty,
        fill_price=price,
        status="filled",
        signal_id=signal_id,
        filled_at=datetime.utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    logger.info(f"Paper order filled: {side} {ticker} {qty:.4f} shares @ ${price:.2f}")
    return {
        "order_id": str(order.id),
        "ticker": ticker,
        "side": side,
        "notional": notional,
        "qty": round(qty, 6),
        "fill_price": round(price, 4),
        "status": "filled",
    }


def close_position(ticker: str, db: Session) -> Optional[dict]:
    pos = db.query(PaperPosition).filter(PaperPosition.ticker == ticker).first()
    if not pos or pos.qty == 0:
        return None

    price = _current_price(ticker)
    if not price:
        return None

    notional = abs(pos.qty * price)
    side = "sell" if pos.qty > 0 else "buy"
    return place_order(ticker, side, notional, db)


def get_recent_orders(db: Session, limit: int = 50) -> list:
    orders = (
        db.query(PaperOrder)
        .order_by(PaperOrder.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "order_id": str(o.id),
            "ticker": o.ticker,
            "side": o.side,
            "qty": round(o.qty, 6),
            "notional": round(o.notional, 2),
            "fill_price": round(o.fill_price, 4) if o.fill_price else None,
            "status": o.status,
            "created_at": str(o.created_at),
            "filled_at": str(o.filled_at) if o.filled_at else None,
        }
        for o in orders
    ]
