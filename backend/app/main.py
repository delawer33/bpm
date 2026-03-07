import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.cache.track_meta import sync_dictionary
from app.core.db import get_db
from app.core.redis import redis_client
from app.exception_handlers import register_exception_handlers
from app.logger_settings import RequestIDFilter

logger = logging.getLogger("app_logger")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_client.ping()  # type: ignore[return-value]
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Redis connection failed: %s", e)
        raise e

    try:
        async for session in get_db():
            await sync_dictionary(redis_client, session)
            break
        logger.info("Redis dictionaries synced from DB")
    except Exception as e:
        logger.error("Failed to sync dictionaries: %s", e)
        raise
    yield

    await redis_client.close()
    logger.info("Redis connection closed")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    request_filter = RequestIDFilter(request_id)
    logger.addFilter(request_filter)

    try:
        response = await call_next(request)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.removeFilter(request_filter)


app.include_router(api_v1_router, prefix="/api/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
