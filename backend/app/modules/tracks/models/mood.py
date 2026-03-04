from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from .track import Track


class Mood(Base):
    __tablename__ = "moods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    tracks: Mapped[List["Track"]] = relationship(
        secondary="track_moods",
        back_populates="moods",
    )


class TrackMood(Base):
    __tablename__ = "track_moods"

    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )

    mood_id: Mapped[int] = mapped_column(
        ForeignKey("moods.id", ondelete="CASCADE"), primary_key=True
    )
