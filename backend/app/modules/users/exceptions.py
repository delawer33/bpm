from app.exceptions import AppBaseException, ErrorCode


class InvalidTokenError(AppBaseException):
    def __init__(self):
        super().__init__("Invalid or expired token", ErrorCode.AUTH_FAILED, 401)


class RefreshTokenExistsError(AppBaseException):
    def __init__(self):
        super().__init__("Something went wrong", ErrorCode.SERVER_ERROR, 500)


class RefreshTokenNotExistError(AppBaseException):
    def __init__(self):
        super().__init__("Invalid or expired token", ErrorCode.AUTH_FAILED, 401)


class RefreshTokenRevokedError(AppBaseException):
    def __init__(self):
        super().__init__("Invalid or expired token", ErrorCode.AUTH_FAILED, 401)


class UserWithEmailExistsError(AppBaseException):
    def __init__(self):
        super().__init__("User with this email already exists", ErrorCode.EMAIL_TAKEN, 400)
