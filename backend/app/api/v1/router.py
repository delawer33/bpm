from fastapi import APIRouter

from app.modules.tracks.routes import router as tracks_router
from app.modules.users.routes import router as users_router

router = APIRouter()
router.include_router(users_router)
router.include_router(tracks_router)
