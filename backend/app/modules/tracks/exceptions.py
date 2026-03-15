from app.exceptions import AppBaseException, ErrorCode


class SlugValidationError(AppBaseException):
    def __init__(self):
        super().__init__("Slug is invalid", ErrorCode.BAD_REQUEST, 400)


class TrackFileValidationError(AppBaseException):
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.BAD_REQUEST, 400)


class TrackNotFoundError(AppBaseException):
    def __init__(self):
        super().__init__("Track not found", ErrorCode.NOT_FOUND, 404)


class InvalidVisibilityStatusError(AppBaseException):
    def __init__(self):
        super().__init__("Invalid track visibility status", ErrorCode.BAD_REQUEST, 400)


class TrackNotFoundOrNoAccessError(AppBaseException):
    def __init__(self):
        super().__init__(
            "Track not found or you don't have access to it", ErrorCode.NOT_FOUND, 404
        )
