import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PGENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base

if TYPE_CHECKING:
    from .track import Track


class TrackFileType(str, Enum):
    PREVIEW = "preview"
    MAIN = "main"
    STEMS = "stems"
    IMAGE = "image"


class TrackFileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TrackFile(Base):
    __tablename__ = "track_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_type: Mapped[TrackFileType] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    status: Mapped[TrackFileStatus] = mapped_column(
        PGENUM(TrackFileStatus, name="track_file_status", create_type=False),
        nullable=False,
        default=TrackFileStatus.PENDING,
        server_default="pending",
        index=True,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    file_name: Mapped[Optional[str]] = mapped_column(String(255))

    file_size: Mapped[Optional[int]] = mapped_column(Integer)

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    mime_type: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="files",
    )
