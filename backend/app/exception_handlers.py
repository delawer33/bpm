import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .exceptions import AppBaseException

logger = logging.getLogger("app_logger")


def register_exception_handlers(app):
    @app.exception_handler(AppBaseException)
    async def app_exc_handler(
        request: Request,
        exc: AppBaseException,
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"AppBaseError: {exc}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "request_id": request_id,
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exc_handler(
        request: Request,
        exc: SQLAlchemyError,
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"SQLAlchemyError: {exc}", exc_info=True, extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": "Internal server error",
                "request_id": request_id,
            },
        )

    @app.exception_handler(OperationalError)
    @app.exception_handler(ConnectionRefusedError)
    async def database_connection_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Database connection failed (likely down/refused)",
            extra={"orig": getattr(exc, "orig", None)},
        )

        return JSONResponse(
            status_code=503,
            content={
                "error": "server_error",
                "message": "Service temporarily unavailable. Database connection error. Please try again in a few moments.",
                "request_id": request_id,
            },
        )
