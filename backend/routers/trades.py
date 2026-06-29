from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.database import get_db
from db.models import Trade
from trading.alpaca_client import get_account, get_positions, get_recent_orders

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/account")
def account():
    return get_account()


@router.get("/positions")
def positions():
    return get_positions()


@router.get("/orders")
def orders(limit: int = Query(50)):
    return get_recent_orders(limit=limit)


@router.get("/history")
def trade_history(
    ticker: str = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db),
):
    q = db.query(Trade).order_by(desc(Trade.created_at))
    if ticker:
        q = q.filter(Trade.ticker == ticker.upper())
    return q.limit(limit).all()
