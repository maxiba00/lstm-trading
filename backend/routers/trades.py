from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from trading.paper_engine import (
    get_account, get_positions, get_recent_orders, close_position, place_order
)

router = APIRouter(prefix="/trades", tags=["trades"])


class OrderRequest(BaseModel):
    ticker: str
    side: str  # "buy" or "sell"
    notional: float
    signal_id: int | None = None


@router.get("/account")
def account(db: Session = Depends(get_db)):
    return get_account(db)


@router.get("/positions")
def positions(db: Session = Depends(get_db)):
    return get_positions(db)


@router.get("/orders")
def orders(limit: int = Query(50), db: Session = Depends(get_db)):
    return get_recent_orders(db, limit=limit)


@router.post("/order")
def order(req: OrderRequest, db: Session = Depends(get_db)):
    if req.side not in ("buy", "sell"):
        return {"error": "side must be 'buy' or 'sell'"}
    result = place_order(req.ticker.upper(), req.side, req.notional, db, signal_id=req.signal_id)
    if not result:
        return {"error": f"Order failed for {req.ticker} (insufficient cash, no position to sell, or price unavailable)"}
    return result


@router.get("/stats")
def trade_stats(db: Session = Depends(get_db)):
    """Win/loss stats from completed round-trips (buy followed by sell for same ticker)."""
    from db.models import PaperOrder
    orders = db.query(PaperOrder).order_by(PaperOrder.created_at).all()

    # Group by ticker, match buy→sell pairs
    from collections import defaultdict
    buy_stack: dict = defaultdict(list)
    trades_pnl = []

    for o in orders:
        if o.fill_price is None:
            continue
        if o.side == "buy":
            buy_stack[o.ticker].append(o)
        elif o.side == "sell" and buy_stack[o.ticker]:
            buy_order = buy_stack[o.ticker].pop(0)
            pnl = (o.fill_price - buy_order.fill_price) * buy_order.qty
            trades_pnl.append(pnl)

    total = len(trades_pnl)
    wins = sum(1 for p in trades_pnl if p > 0)
    losses = sum(1 for p in trades_pnl if p <= 0)
    total_pnl = sum(trades_pnl)
    avg_win = sum(p for p in trades_pnl if p > 0) / wins if wins else 0
    avg_loss = sum(p for p in trades_pnl if p <= 0) / losses if losses else 0

    return {
        "total_closed_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total else 0,
        "total_realized_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
        "total_orders": len(orders),
        "open_positions": db.query(PaperOrder).filter(PaperOrder.status == "filled").count(),
    }


@router.post("/close/{ticker}")
def close(ticker: str, db: Session = Depends(get_db)):
    result = close_position(ticker.upper(), db)
    if not result:
        return {"error": f"No open position for {ticker}"}
    return result
