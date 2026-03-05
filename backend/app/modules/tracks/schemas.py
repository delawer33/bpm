import uuid
from typing import Annotated, List

from pydantic import BaseModel, Field, field_validator


class STrackID(BaseModel):
    track_id: uuid.UUID


class STrackUpload(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    bpm: Annotated[int, Field(gt=0, le=300)]
    root_note: str
    scale_type: str
    tags: List[str] = []
    genres: List[str] = []
    moods: List[str] = []
    instruments: List[str] = []

    description: str | None = None

    @field_validator("root_note")
    @classmethod
    def validate_root_note(cls, v: str) -> str:
        allowed = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}
        if v not in allowed:
            raise ValueError(f"root_note must be one of {allowed}")
        return v

    @field_validator("scale_type")
    @classmethod
    def validate_scale_type(cls, v: str) -> str:
        allowed = {"major", "minor"}
        if v not in allowed:
            raise ValueError(f"scale_type must be one of {allowed}")
        return v

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one genre is required")
        return v

    @field_validator("instruments")
    @classmethod
    def validate_instruments(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one instrument is required")
        return v
