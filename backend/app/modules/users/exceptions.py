from app.exceptions import AppBaseException


class InvalidTokenError(AppBaseException):
    def __init__(self):
        super().__init__("Token is invalid", "token_invalid", 400)


class RefreshTokenExistsError(AppBaseException):
    def __init__(self):
        super().__init__("Token already exists in db", "refresh_token_exists", 500)


class RefreshTokenNotExistError(AppBaseException):
    def __init__(self):
        super().__init__("Refresh token does not exist", "refresh_token_not_exists", 400)


class RefreshTokenRevokedError(AppBaseException):
    def __init__(self):
        super().__init__("Refresh token is revoked", "refresh_token_revoked", 400)


class UserWithEmailExistsError(AppBaseException):
    def __init__(self):
        super().__init__("User with this email already exists", "user_with_email_exists", 400)
