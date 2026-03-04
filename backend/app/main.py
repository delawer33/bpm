import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import router as api_v1_router
from .exception_handlers import register_exception_handlers
from .logger_settings import RequestIDFilter

logger = logging.getLogger("app_logger")

app = FastAPI()


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
