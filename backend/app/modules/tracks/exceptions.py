from app.exceptions import AppBaseException


class SlugValidationError(AppBaseException):
    def __init__(self):
        super().__init__("Slug is invalid", "slug_invalid", 400)


class TrackIsNotFoundOrNoAccessError(AppBaseException):
    def __init__(self):
        super().__init__(
            "Track not found or you don't have access to it", "track_not_found_or_no_access", 400
        )
