from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse

from forest_ensys.api import api_router
from forest_ensys.core import settings
from forest_ensys.database import init_db

# Create FastAPI app and add all endpoints
app = FastAPI(
    title=settings.SERVER_NAME,
    root_path="/api",
)
app.include_router(api_router)


# Initialize database and create models
@app.on_event("startup")
def init_database():
    init_db.check_connection()
    init_db.create_all()


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )
