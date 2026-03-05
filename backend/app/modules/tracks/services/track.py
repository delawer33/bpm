import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracks.models.track import Track


class TrackService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_draft(self, user_id: uuid.UUID) -> Track:
        track = Track(user_id=user_id)
        self.db.add(track)
        await self.db.flush()
        return track
