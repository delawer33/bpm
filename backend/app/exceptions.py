class ErrorCode:
    AUTH_FAILED = "auth_failed"
    EMAIL_TAKEN = "email_taken"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    BAD_REQUEST = "bad_request"
    VALIDATION_ERROR = "validation_error"
    SERVER_ERROR = "server_error"


class AppBaseException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)
