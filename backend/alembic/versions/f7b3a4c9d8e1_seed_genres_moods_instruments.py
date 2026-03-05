"""seed genres, moods, instruments with fixed ids and slugs

Revision ID: f7b3a4c9d8e1
Revises: e1052da65a67
Create Date: 2026-03-05 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7b3a4c9d8e1"
down_revision: Union[str, Sequence[str], None] = "e1052da65a67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GENRES = [
    (1, "Hip-Hop", "hip-hop"),
    (2, "Trap", "trap"),
    (3, "Rap", "rap"),
    (4, "RnB", "rnb"),
    (5, "Pop", "pop"),
    (6, "Afrobeats", "afrobeats"),
    (7, "Drill", "drill"),
    (8, "Boom Bap", "boom-bap"),
    (9, "Lo-Fi", "lofi"),
    (10, "Reggaeton", "reggaeton"),
    (11, "Dancehall", "dancehall"),
    (12, "EDM", "edm"),
    (13, "House", "house"),
    (14, "Techno", "techno"),
    (15, "Rock", "rock"),
    (16, "Alternative", "alternative"),
    (17, "Country", "country"),
    (18, "Latin", "latin"),
    (19, "Jazz", "jazz"),
    (20, "Classical", "classical"),
]


MOODS = [
    (1, "Aggressive", "aggressive"),
    (2, "Angry", "angry"),
    (3, "Dark", "dark"),
    (4, "Epic", "epic"),
    (5, "Sad", "sad"),
    (6, "Emotional", "emotional"),
    (7, "Chill", "chill"),
    (8, "Laid Back", "laid-back"),
    (9, "Happy", "happy"),
    (10, "Uplifting", "uplifting"),
    (11, "Motivational", "motivational"),
    (12, "Bouncy", "bouncy"),
    (13, "Melodic", "melodic"),
    (14, "Dark Trap", "dark-trap"),
    (15, "Dreamy", "dreamy"),
]


INSTRUMENTS = [
    (1, "Piano", "piano"),
    (2, "Keys", "keys"),
    (3, "Guitar", "guitar"),
    (4, "Electric Guitar", "electric-guitar"),
    (5, "Acoustic Guitar", "acoustic-guitar"),
    (6, "Bass", "bass"),
    (7, "808", "808"),
    (8, "Strings", "strings"),
    (9, "Synth", "synth"),
    (10, "Pad", "pad"),
    (11, "Pluck", "pluck"),
    (12, "Bell", "bell"),
    (13, "Flute", "flute"),
    (14, "Brass", "brass"),
    (15, "Vocal", "vocal"),
    (16, "Choir", "choir"),
    (17, "Drums", "drums"),
    (18, "Percussion", "percussion"),
    (19, "Lead", "lead"),
    (20, "Arp", "arp"),
]


def upgrade() -> None:
    genres_table = sa.table(
        "genres",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )
    moods_table = sa.table(
        "moods",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )
    instruments_table = sa.table(
        "instruments",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )

    op.bulk_insert(
        genres_table,
        [{"id": id_, "name": name, "slug": slug} for id_, name, slug in GENRES],
    )
    op.bulk_insert(
        moods_table,
        [{"id": id_, "name": name, "slug": slug} for id_, name, slug in MOODS],
    )
    op.bulk_insert(
        instruments_table,
        [{"id": id_, "name": name, "slug": slug} for id_, name, slug in INSTRUMENTS],
    )


def downgrade() -> None:
    genre_ids = ", ".join(str(id_) for id_, _, _ in GENRES)
    mood_ids = ", ".join(str(id_) for id_, _, _ in MOODS)
    instrument_ids = ", ".join(str(id_) for id_, _, _ in INSTRUMENTS)

    op.execute(sa.text(f"DELETE FROM genres WHERE id IN ({genre_ids})"))
    op.execute(sa.text(f"DELETE FROM moods WHERE id IN ({mood_ids})"))
    op.execute(sa.text(f"DELETE FROM instruments WHERE id IN ({instrument_ids})"))

