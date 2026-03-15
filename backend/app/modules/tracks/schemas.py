import uuid
from datetime import datetime
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.tracks.models.track import TrackStatus, TrackVisibility

ROOT_NOTES = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}
SCALE_TYPES = {"major", "minor"}


class STrackFileUploadRequest(BaseModel):
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    size: Annotated[int, Field(gt=0)]
    mime: Annotated[str, Field(min_length=1, max_length=100)]


class STrackFileUploadResponse(BaseModel):
    uploadUrl: str


class STrackID(BaseModel):
    track_id: uuid.UUID


class STrackUpload(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    bpm: Annotated[int, Field(gt=0, le=300)]
    root_note: str
    scale_type: str
    tags: List[str]
    genres: List[str]
    moods: List[str]
    instruments: List[str]
    visibility: str
    description: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("root_note")
    @classmethod
    def validate_root_note(cls, v: str) -> str:
        if v not in ROOT_NOTES:
            raise ValueError(f"root_note must be one of {ROOT_NOTES}")
        return v

    @field_validator("scale_type")
    @classmethod
    def validate_scale_type(cls, v: str) -> str:
        if v not in SCALE_TYPES:
            raise ValueError(f"scale_type must be one of {SCALE_TYPES}")
        return v

    @field_validator("moods")
    @classmethod
    def validate_moods(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one mood is required")
        return v

    @field_validator("instruments")
    @classmethod
    def validate_instruments(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one instrument is required")
        return v

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one instrument is required")
        if len(v) > 2:
            raise ValueError("Maximum 2 genres")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: List[str]) -> List[str]:
        if v not in TrackVisibility:
            raise ValueError("Track visibility can be public, private or unlisted")
        return v


class SSlugItem(BaseModel):
    slug: str

    model_config = ConfigDict(from_attributes=True)


class STagItem(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class STrackFileResponse(BaseModel):
    id: uuid.UUID
    file_type: str
    file_name: str
    status: str
    file_size: int

    model_config = ConfigDict(from_attributes=True)


class STrackFileDetailResponse(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    file_type: str
    status: str
    storage_key: str
    file_name: str | None
    file_size: int | None
    duration_seconds: int | None
    mime_type: str | None
    created_at: datetime
    url: str

    model_config = ConfigDict(from_attributes=True)


class STrackListFilters(BaseModel):
    status: List[TrackStatus] | None = None
    bpm_min: Annotated[int | None, Field(None, ge=1, le=300)] = None
    bpm_max: Annotated[int | None, Field(None, ge=1, le=300)] = None
    root_note: List[str] | None = None
    scale_type: List[str] | None = None
    visibility: List[TrackVisibility] | None = None
    limit: Annotated[int, Field(default=20, ge=1, le=100)] = 20
    cursor: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("root_note")
    @classmethod
    def validate_root_notes(cls, v: List[str] | None) -> List[str] | None:
        if not v:
            return v
        invalid = set(v) - ROOT_NOTES
        if invalid:
            raise ValueError(f"root_note must be one of {ROOT_NOTES}")
        return v

    @field_validator("scale_type")
    @classmethod
    def validate_scale_types(cls, v: List[str] | None) -> List[str] | None:
        if not v:
            return v
        invalid = set(v) - SCALE_TYPES
        if invalid:
            raise ValueError(f"scale_type must be one of {SCALE_TYPES}")
        return v


class STrackListItem(BaseModel):
    id: uuid.UUID
    title: str | None
    description: str | None
    bpm: int | None
    root_note: str | None
    scale_type: str | None
    status: str
    visibility: TrackVisibility
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class STrackListResponse(BaseModel):
    items: list[STrackListItem]
    next_cursor: str | None


class STrackOwnerResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    description: str | None
    bpm: int | None
    root_note: str | None
    scale_type: str | None

    status: str
    visibility: TrackVisibility

    files: list[STrackFileResponse]

    created_at: datetime
    updated_at: datetime

    tags: list[STagItem]
    genres: list[SSlugItem]
    moods: list[SSlugItem]
    instruments: list[SSlugItem]

    model_config = ConfigDict(from_attributes=True)
