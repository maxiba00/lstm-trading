from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.database import get_db
from db.models import Signal

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/")
def list_signals(
    ticker: str = Query(None),
    signal_type: str = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db),
):
    q = db.query(Signal).order_by(desc(Signal.created_at))
    if ticker:
        q = q.filter(Signal.ticker == ticker.upper())
    if signal_type:
        q = q.filter(Signal.signal == signal_type.upper())
    return q.limit(limit).all()


@router.get("/latest")
def latest_signals(db: Session = Depends(get_db)):
    """One signal per ticker, most recent."""
    from sqlalchemy import func
    subq = (
        db.query(Signal.ticker, func.max(Signal.created_at).label("max_ts"))
        .group_by(Signal.ticker)
        .subquery()
    )
    rows = (
        db.query(Signal)
        .join(subq, (Signal.ticker == subq.c.ticker) & (Signal.created_at == subq.c.max_ts))
        .all()
    )
    return rows


@router.get("/stats")
def signal_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    counts = (
        db.query(Signal.signal, func.count(Signal.id))
        .group_by(Signal.signal)
        .all()
    )
    return {row[0]: row[1] for row in counts}
