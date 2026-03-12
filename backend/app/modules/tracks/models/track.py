import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    UUID,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import ENUM as PGENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base

from .genre import Genre
from .instrument import Instrument
from .mood import Mood
from .tag import Tag
from .thumbnail import Thumbnail
from .track_file import TrackFile


class TrackStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TrackVisibility(str, Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class Track(Base):
    __tablename__ = "tracks"

    __table_args__ = (
        CheckConstraint(
            "(bpm IS NULL) OR (bpm > 0 AND bpm <= 300)",
            name="check_bpm_range",
        ),
        CheckConstraint(
            "(root_note IS NULL) OR "
            "root_note IN ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')",
            name="check_root_note",
        ),
        CheckConstraint(
            "(scale_type IS NULL) OR scale_type IN ('major','minor')",
            name="check_scale_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(String(500))

    bpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    root_note: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    scale_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    status: Mapped[TrackStatus] = mapped_column(
        PGENUM(TrackStatus, name="track_status", create_type=False),
        nullable=False,
        default=TrackStatus.DRAFT,
        index=True,
    )

    visibility: Mapped[TrackVisibility] = mapped_column(
        PGENUM(TrackVisibility, name="track_visibility", create_type=False),
        nullable=False,
        default=TrackVisibility.PUBLIC,
        server_default="PUBLIC",
        index=True,
    )

    waveform_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    files: Mapped[list["TrackFile"]] = relationship(
        "TrackFile",
        back_populates="track",
        cascade="all, delete-orphan",
    )

    thumbnails: Mapped[list["Thumbnail"]] = relationship(
        "Thumbnail",
        back_populates="track",
        cascade="all, delete-orphan",
    )

    tags: Mapped[List["Tag"]] = relationship(
        secondary="track_tags",
        back_populates="tracks",
    )

    genres: Mapped[List["Genre"]] = relationship(
        secondary="track_genres",
        back_populates="tracks",
    )

    moods: Mapped[List["Mood"]] = relationship(
        secondary="track_moods",
        back_populates="tracks",
    )

    instruments: Mapped[List["Instrument"]] = relationship(
        secondary="track_instruments",
        back_populates="tracks",
    )
