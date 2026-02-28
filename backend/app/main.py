from fastapi import FastAPI

from .api.v1.router import router as api_v1_router
from .exception_handlers import register_exception_handlers

app = FastAPI()
app.include_router(api_v1_router, prefix="/api/v1")
register_exception_handlers(app)
