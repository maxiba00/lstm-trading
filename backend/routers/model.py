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

# In-memory training status — single worker process, lost on restart (acceptable for this use case).
TRAINING_STATUS = {
    "is_training": False,
    "current_ticker": None,
    "queue": [],
    "completed": [],
    "failed": [],
}


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
    include_trends: bool = False
    include_sentiment: bool = True
    include_fred: bool = True


def _run_training(tickers: list, params: dict, db_url: str):
    """Background training task — runs in thread pool."""
    import logging
    from db.database import SessionLocal
    from db.models import ModelRun

    logger = logging.getLogger(__name__)
    TRAINING_STATUS["is_training"] = True
    TRAINING_STATUS["queue"] = list(tickers)
    TRAINING_STATUS["completed"] = []
    TRAINING_STATUS["failed"] = []
    db = SessionLocal()
    try:
        for ticker in tickers:
            TRAINING_STATUS["current_ticker"] = ticker
            TRAINING_STATUS["queue"] = [t for t in TRAINING_STATUS["queue"] if t != ticker]
            try:
                result = train_ticker(ticker, **params)
            except Exception as e:
                logger.error(f"Training failed for {ticker}: {e}")
                result = None
            if result:
                # Delete old run for this ticker before inserting new one
                db.query(ModelRun).filter(ModelRun.ticker == ticker).delete()
                run = ModelRun(**result, params=params)
                db.add(run)
                db.commit()
                TRAINING_STATUS["completed"].append(ticker)
                logger.info(f"Saved ModelRun for {ticker}")
            else:
                TRAINING_STATUS["failed"].append(ticker)
    finally:
        db.close()
        TRAINING_STATUS["is_training"] = False
        TRAINING_STATUS["current_ticker"] = None


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
        include_fred=req.include_fred,
    )
    from db.database import DATABASE_URL
    background_tasks.add_task(_run_training, tickers, params, DATABASE_URL)
    return {"message": f"Training started for {len(tickers)} tickers", "tickers": tickers}


@router.get("/training-status")
def training_status():
    return TRAINING_STATUS


@router.get("/status")
def model_status(db: Session = Depends(get_db)):
    """Which tickers have trained models (based on DB runs, not legacy .keras files)."""
    trained = [r.ticker for r in db.query(ModelRun.ticker).distinct().all()]
    return {
        "trained_count": len(trained),
        "trained_tickers": trained,
        "available_tickers": SP100_TICKERS,
    }


@router.get("/runs")
def model_runs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ModelRun).order_by(desc(ModelRun.created_at)).limit(limit).all()
