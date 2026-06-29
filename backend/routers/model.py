import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.database import get_db
from db.models import ModelRun
from data.fetcher import SP100_TICKERS
from model.train import train_ticker, train_all

MODELS_DIR = Path(__file__).parent.parent / "models"

router = APIRouter(prefix="/model", tags=["model"])


class TrainRequest(BaseModel):
    tickers: list[str] | None = None
    start: str = "2014-01-01"
    end: str = "2024-12-31"
    step_size: int = 60
    train_ratio: float = 0.7
    epochs: int = 100
    batch_size: int = 32
    lstm_units: int = 50
    dropout: float = 0.3
    include_wiki: bool = True
    include_trends: bool = True
    include_sentiment: bool = True


def _run_training(tickers: list, params: dict, db_url: str):
    """Background training task — runs in thread pool."""
    import logging
    from db.database import SessionLocal
    from db.models import ModelRun

    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        for ticker in tickers:
            result = train_ticker(ticker, **params)
            if result:
                run = ModelRun(**result, params=params)
                db.add(run)
                db.commit()
                logger.info(f"Saved ModelRun for {ticker}")
    finally:
        db.close()


@router.post("/train")
def trigger_training(
    req: TrainRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    tickers = req.tickers or SP100_TICKERS[:10]  # default: first 10 for quick start
    params = dict(
        start=req.start, end=req.end, step_size=req.step_size, train_ratio=req.train_ratio,
        epochs=req.epochs, batch_size=req.batch_size, lstm_units=req.lstm_units,
        dropout=req.dropout, include_wiki=req.include_wiki,
        include_trends=req.include_trends, include_sentiment=req.include_sentiment,
    )
    from db.database import DATABASE_URL
    background_tasks.add_task(_run_training, tickers, params, DATABASE_URL)
    return {"message": f"Training started for {len(tickers)} tickers", "tickers": tickers}


@router.get("/status")
def model_status():
    """Which tickers have trained models."""
    trained = [p.stem for p in MODELS_DIR.glob("*.keras")]
    return {
        "trained_count": len(trained),
        "trained_tickers": sorted(trained),
        "available_tickers": SP100_TICKERS,
    }


@router.get("/runs")
def model_runs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ModelRun).order_by(desc(ModelRun.created_at)).limit(limit).all()
