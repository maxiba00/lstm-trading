"""
Persistent settings — stored in DB, editable from the frontend.
All trading parameters live here so the user can tweak without redeploying.
"""

import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Settings as SettingsModel

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULTS = {
    "min_return_pct": 1.0,          # minimum predicted return to trigger signal
    "min_confidence": 0.60,          # minimum MC Dropout confidence
    "allow_short": True,             # allow SHORT signals
    "position_size_usd": 1000.0,    # dollar amount per trade
    "max_positions": 10,             # max simultaneous open positions
    "stop_loss_pct": 2.0,           # stop loss in %
    "tickers": [],                   # empty = use all trained tickers
    "run_time": "16:30",            # daily run time (after US market close, ET)
    "eodhd_api_key": "",
}


class SettingsUpdate(BaseModel):
    min_return_pct: float = None
    min_confidence: float = None
    allow_short: bool = None
    position_size_usd: float = None
    max_positions: int = None
    stop_loss_pct: float = None
    tickers: list[str] = None
    run_time: str = None
    eodhd_api_key: str = None


def _get(key: str, db: Session):
    row = db.query(SettingsModel).filter(SettingsModel.key == key).first()
    if row is None:
        return DEFAULTS.get(key)
    val = row.value
    try:
        return json.loads(val)
    except Exception:
        return val


def _set(key: str, value, db: Session):
    row = db.query(SettingsModel).filter(SettingsModel.key == key).first()
    serialized = json.dumps(value)
    if row:
        row.value = serialized
    else:
        row = SettingsModel(key=key, value=serialized)
        db.add(row)
    db.commit()


@router.get("/")
def get_all_settings(db: Session = Depends(get_db)):
    result = {}
    for key, default in DEFAULTS.items():
        result[key] = _get(key, db)
        if result[key] is None:
            result[key] = default
    return result


@router.put("/")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    for key, value in updates.items():
        _set(key, value, db)
    return {"updated": list(updates.keys())}


def load_settings(db: Session) -> dict:
    """Helper used by scheduler and signal router."""
    result = {}
    for key, default in DEFAULTS.items():
        val = _get(key, db)
        result[key] = val if val is not None else default
    return result
