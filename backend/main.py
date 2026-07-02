import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import engine, Base
from db.models import Signal, Trade, ModelRun, Settings
from routers import signals, trades, model, settings
from scheduler import start_scheduler, stop_scheduler, run_daily_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="LSTM Trading System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router)
app.include_router(trades.router)
app.include_router(model.router)
app.include_router(settings.router)


@app.get("/health")
def health():
    return {"status": "ok"}


_pipeline_running = False

@app.post("/pipeline/run-now")
def run_now():
    """Manually trigger the daily pipeline — blocked if already running."""
    global _pipeline_running
    if _pipeline_running:
        return {"message": "Pipeline already running — please wait"}
    import threading
    def _guarded():
        global _pipeline_running
        _pipeline_running = True
        try:
            run_daily_pipeline()
        finally:
            _pipeline_running = False
    threading.Thread(target=_guarded, daemon=True).start()
    return {"message": "Pipeline triggered"}
