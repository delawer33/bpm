from app.exceptions import AppBaseException


class RefreshTokenExistsError(AppBaseException):
    def __init__(self):
        super().__init__("Token already exists in db", "refresh_token_exists", 500)
