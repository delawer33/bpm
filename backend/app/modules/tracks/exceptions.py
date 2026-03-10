from app.exceptions import AppBaseException


class SlugValidationError(AppBaseException):
    def __init__(self):
        super().__init__("Slug is invalid", "slug_invalid", 400)


class TrackFileValidationError(AppBaseException):
    def __init__(self, message: str):
        super().__init__(message, "file_invalid", 400)


class TrackNotFoundError(AppBaseException):
    def __init__(self):
        super().__init__("Track not found", "track_not_found", 400)


class InvalidVisibilityStatusError(AppBaseException):
    def __init__(self):
        super().__init__("Invalid track visibility status", "ivalid_track_visibility_status", 400)


class TrackNotFoundOrNoAccessError(AppBaseException):
    def __init__(self):
        super().__init__(
            "Track not found or you don't have access to it", "track_not_found_or_no_access", 400
        )
