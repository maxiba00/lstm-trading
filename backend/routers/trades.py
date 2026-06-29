from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from trading.paper_engine import (
    get_account, get_positions, get_recent_orders, close_position
)

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/account")
def account(db: Session = Depends(get_db)):
    return get_account(db)


@router.get("/positions")
def positions(db: Session = Depends(get_db)):
    return get_positions(db)


@router.get("/orders")
def orders(limit: int = Query(50), db: Session = Depends(get_db)):
    return get_recent_orders(db, limit=limit)


@router.post("/close/{ticker}")
def close(ticker: str, db: Session = Depends(get_db)):
    result = close_position(ticker.upper(), db)
    if not result:
        return {"error": f"No open position for {ticker}"}
    return result
