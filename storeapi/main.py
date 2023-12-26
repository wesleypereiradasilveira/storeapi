import logging
import sentry_sdk
from contextlib import asynccontextmanager
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler
from storeapi.routers.post import router as post_router
from storeapi.routers.user import router as user_router
from storeapi.routers.upload import router as upload_router
from storeapi.database import database
from storeapi.logging_conf import configure_logging
from storeapi.config import config

def configure_sentry() -> None:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0
    )

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_sentry()
    configure_logging()
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(post_router)
app.include_router(user_router)
app.include_router(upload_router)

@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exec):
    logger.error(f"HTTPException: {exec.status_code} {exec.detail}")
    return await http_exception_handler(request, exec)

@app.get("/")
async def root():
    return {"message": "Hello, world!"}

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1/0
    return division_by_zero
