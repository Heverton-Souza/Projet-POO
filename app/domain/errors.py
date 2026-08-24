class AppError(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 422)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Autenticação necessária."):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Você não possui permissão para realizar esta ação."):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Recurso"):
        super().__init__(f"{resource} não encontrado.", "NOT_FOUND", 404)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)

