"""
Daily trading scheduler.
Runs after US market close (configurable in settings, default 16:30 ET).
Pipeline: fetch data → predict → generate signals → execute paper trades → persist.
"""

import logging
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

_scheduler = None


def run_daily_pipeline():
    """Full daily pipeline: predict all trained tickers, generate signals, execute trades."""
    from pathlib import Path
    from db.database import SessionLocal
    from db.models import Signal as SignalModel, Trade as TradeModel
    from db.models import Settings as SettingsModel
    from routers.settings import load_settings
    from model.predict import predict_next_day
    from trading.signal import generate_signals, Signal
    from trading.paper_engine import place_order, get_positions, get_account, close_position

    db = SessionLocal()
    try:
        settings = load_settings(db)
        min_return = settings["min_return_pct"]
        min_conf = settings["min_confidence"]
        allow_short = settings["allow_short"]
        pos_size = settings["position_size_usd"]
        max_pos = settings["max_positions"]

        models_dir = Path(__file__).parent / "models"
        trained = [p.stem for p in models_dir.glob("*.keras")]

        tickers = settings.get("tickers") or trained
        if not tickers:
            logger.warning("No trained models found — skipping pipeline")
            return

        logger.info(f"Running pipeline for {len(tickers)} tickers")

        # 1. Predict
        predictions = []
        for ticker in tickers:
            try:
                pred = predict_next_day(ticker)
                if pred:
                    predictions.append(pred)
            except Exception as e:
                logger.error(f"Prediction failed for {ticker}: {e}")

        # 2. Generate signals
        trade_signals = generate_signals(
            predictions,
            min_return_pct=min_return,
            min_confidence=min_conf,
            allow_short=allow_short,
        )

        # 3. Persist signals — one per ticker per calendar day (no duplicates)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for sig in trade_signals:
            existing = db.query(SignalModel).filter(
                SignalModel.ticker == sig.ticker,
                SignalModel.created_at >= today_start,
            ).first()
            if existing:
                logger.info(f"Signal for {sig.ticker} already exists today — skipping duplicate")
                continue
            row = SignalModel(
                ticker=sig.ticker,
                signal=sig.signal.value,
                current_price=sig.current_price,
                predicted_price=sig.predicted_price,
                predicted_return_pct=sig.predicted_return_pct,
                confidence=sig.confidence,
                mc_std=sig.mc_std,
                reason=sig.reason,
                min_return_pct=min_return,
                min_confidence=min_conf,
            )
            db.add(row)
        db.commit()

        # 4. Auto take-profit: close positions that have reached stop_loss_pct gain
        take_profit_pct = settings.get("stop_loss_pct", 2.0)
        try:
            open_positions = get_positions(db)
            for pos in open_positions:
                if pos["unrealized_plpc"] >= take_profit_pct:
                    close_position(pos["ticker"], db)
                    logger.info(f"Take-profit triggered for {pos['ticker']} (+{pos['unrealized_plpc']:.1f}%)")
                elif pos["unrealized_plpc"] <= -take_profit_pct:
                    close_position(pos["ticker"], db)
                    logger.info(f"Stop-loss triggered for {pos['ticker']} ({pos['unrealized_plpc']:.1f}%)")
        except Exception as e:
            logger.error(f"Take-profit/stop-loss check failed: {e}")

        # 5. Check current position count before placing new trades
        try:
            current_positions = get_positions(db)
            n_open = len(current_positions)
        except Exception:
            n_open = 0

        # 6. Execute actionable signals
        for sig in trade_signals:
            if sig.signal == Signal.HOLD:
                continue
            if n_open >= max_pos:
                logger.info(f"Max positions ({max_pos}) reached — skipping {sig.ticker}")
                continue

            side = "buy" if sig.signal == Signal.LONG else "sell"
            order = None
            try:
                order = place_order(sig.ticker, side, pos_size, db)
            except Exception as e:
                logger.error(f"Trade execution failed for {sig.ticker}: {e}")

            if order:
                trade_row = TradeModel(
                    ticker=sig.ticker,
                    side=side,
                    notional=pos_size,
                    order_id=order["order_id"],
                    status=order["status"],
                )
                db.add(trade_row)
                db.commit()
                n_open += 1
                logger.info(f"Executed {side} {sig.ticker} ${pos_size}")

        logger.info(f"Pipeline complete — {len(trade_signals)} signals, {n_open} positions")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler(run_time: str = "16:30"):
    global _scheduler
    hour, minute = map(int, run_time.split(":"))

    _scheduler = BackgroundScheduler(timezone=pytz.timezone("US/Eastern"))
    _scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri"),
        id="daily_pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Scheduler started — daily pipeline at {run_time} ET (Mon–Fri)")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
