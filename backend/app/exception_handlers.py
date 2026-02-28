import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import AppBaseException

logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    @app.exception_handler(AppBaseException)
    async def app_exc_handler(
        request: Request,
        exc: AppBaseException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
        )
