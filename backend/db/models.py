from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON

from db.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ticker = Column(String(10), index=True)
    signal = Column(String(5))          # LONG / SHORT / HOLD
    current_price = Column(Float)
    predicted_price = Column(Float)
    predicted_return_pct = Column(Float)
    confidence = Column(Float)
    mc_std = Column(Float)
    reason = Column(Text)
    # Thresholds used when this signal was generated
    min_return_pct = Column(Float)
    min_confidence = Column(Float)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ticker = Column(String(10), index=True)
    side = Column(String(5))            # buy / sell
    notional = Column(Float)
    order_id = Column(String(64), unique=True)
    status = Column(String(20))
    signal_id = Column(Integer)
    filled_avg_price = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_price = Column(Float, nullable=True)
    realized_pnl = Column(Float, nullable=True)


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ticker = Column(String(10))
    mse = Column(Float)
    rmse = Column(Float)
    directional_accuracy = Column(Float)
    n_features = Column(Integer)
    train_samples = Column(Integer)
    test_samples = Column(Integer)
    epochs_run = Column(Integer)
    params = Column(JSON, nullable=True)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperAccount(Base):
    __tablename__ = "paper_account"

    id = Column(Integer, primary_key=True)
    cash = Column(Float, default=100_000.0)
    starting_cash = Column(Float, default=100_000.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, index=True)
    qty = Column(Float, default=0.0)
    avg_entry_price = Column(Float)
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    filled_at = Column(DateTime, nullable=True)
    ticker = Column(String(10), index=True)
    side = Column(String(5))
    notional = Column(Float)
    qty = Column(Float)
    fill_price = Column(Float, nullable=True)
    status = Column(String(20), default="filled")
    signal_id = Column(Integer, nullable=True)
