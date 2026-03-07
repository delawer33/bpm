from app.exceptions import AppBaseException


class InvalidGenreError(AppBaseException):
    def __init__(self):
        super().__init__("Genre is invalid", "genre_invalid", 400)


class InvalidMoodError(AppBaseException):
    def __init__(self):
        super().__init__("Mood is invalid", "mood_invalid", 400)


class InvalidInstrumentError(AppBaseException):
    def __init__(self):
        super().__init__("Instrument is invalid", "instrument_invalid", 400)
