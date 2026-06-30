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


@router.get("/distribution")
def signal_distribution(db: Session = Depends(get_db)):
    """Binned distributions of predicted_return_pct and confidence for histogram charts."""
    import numpy as np
    rows = db.query(Signal.predicted_return_pct, Signal.confidence, Signal.signal).all()
    if not rows:
        return {"return_bins": [], "confidence_bins": []}

    returns = [r[0] for r in rows if r[0] is not None]
    confidences = [r[1] for r in rows if r[1] is not None]

    # Return distribution: bins from -5% to +5%
    return_edges = np.arange(-5.0, 5.5, 0.5)
    return_counts, _ = np.histogram(returns, bins=return_edges)
    return_bins = [
        {"bin": f"{return_edges[i]:.1f}%", "count": int(return_counts[i])}
        for i in range(len(return_counts))
    ]

    # Confidence distribution: bins 0-100%
    conf_edges = np.arange(0, 1.05, 0.05)
    conf_counts, _ = np.histogram(confidences, bins=conf_edges)
    conf_bins = [
        {"bin": f"{int(conf_edges[i]*100)}%", "count": int(conf_counts[i])}
        for i in range(len(conf_counts))
    ]

    # Directional accuracy: did predicted return sign match signal?
    n_correct = sum(1 for r in rows if
        (r[2] == "LONG" and r[0] is not None and r[0] > 0) or
        (r[2] == "SHORT" and r[0] is not None and r[0] < 0) or
        (r[2] == "HOLD")
    )
    n_actionable = sum(1 for r in rows if r[2] in ("LONG", "SHORT"))

    return {
        "return_bins": return_bins,
        "confidence_bins": conf_bins,
        "total_signals": len(rows),
        "n_long": sum(1 for r in rows if r[2] == "LONG"),
        "n_short": sum(1 for r in rows if r[2] == "SHORT"),
        "n_hold": sum(1 for r in rows if r[2] == "HOLD"),
        "avg_return_pct": round(float(np.mean(returns)), 4) if returns else 0,
        "avg_confidence": round(float(np.mean(confidences)), 4) if confidences else 0,
        "signal_alignment_pct": round(n_correct / len(rows) * 100, 1) if rows else 0,
    }
