from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from forest_ensys.api import api_router
from forest_ensys.core import settings
from forest_ensys.database import init_db
from forest_ensys.api.endpoints.grid_data import update_grid_data_logic
from forest_ensys.api.endpoints.grid_data import keys as COMMODITY_KEYS

logger = logging.getLogger(__name__)

def run_grid_update():
    """Scheduled job wrapper - creates its own DB session"""
    from forest_ensys.database import SessionLocal
    db = SessionLocal()
    try:
        result = update_grid_data_logic(db, COMMODITY_KEYS)
        logger.info(f"Grid data update completed: {result}")
    except Exception as e:
        logger.error(f"Grid data update failed: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan - handles startup and shutdown"""
    
    # Startup
    init_db.check_connection()
    init_db.create_all()
    
    # Start scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_grid_update,
        trigger=CronTrigger(minute=5),
        id="grid_data_update",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Grid data scheduler started (runs every hour at :05)")
    
    yield
    
    # Shutdown
    scheduler.shutdown(wait=True)
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.SERVER_NAME,
    root_path="/api",
    lifespan=lifespan,
)

app.include_router(api_router)

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )