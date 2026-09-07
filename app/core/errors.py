"""Error types the API raises deliberately, and their HTTP mapping."""

from fastapi import HTTPException, status


class AppError(Exception):
    """Base for errors we raise on purpose, as opposed to bugs."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def as_http(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={"code": self.code, "message": self.message},
        )


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ProviderUnavailableError(AppError):
    """An upstream AI or logistics provider failed. Callers may retry or fall back."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "provider_unavailable"


class BelowWageFloorError(AppError):
    """A price was submitted below what the artisan's own labour is worth."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "below_wage_floor"
