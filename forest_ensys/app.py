from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from forest_ensys.api import api_router
from forest_ensys.core import settings
from forest_ensys.database import init_db
from forest_ensys.database.session import SessionLocal
from forest_ensys.api.endpoints.grid_data import update_grid_data_logic, keys


def _run_grid_update():
    db = SessionLocal()
    try:
        update_grid_data_logic(db, keys)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db.check_connection()
    init_db.create_all()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_grid_update,
        trigger=CronTrigger(minute=60),
        id="grid_data_update",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=True)


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
