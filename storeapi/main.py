import logging
from contextlib import asynccontextmanager
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler
from storeapi.routers.post import router as post_router
from storeapi.routers.user import router as user_router
from storeapi.routers.upload import router as upload_router
from storeapi.database import database
from storeapi.logging_conf import configure_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
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
