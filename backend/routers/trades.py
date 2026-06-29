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


@router.post("/close/{ticker}")
def close(ticker: str, db: Session = Depends(get_db)):
    result = close_position(ticker.upper(), db)
    if not result:
        return {"error": f"No open position for {ticker}"}
    return result
