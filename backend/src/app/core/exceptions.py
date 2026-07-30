"""Centralized Exception Hierarchy extending FastAPI HTTPException."""

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base Application Exception for standardized HTTP error responses."""

    def __init__(self, status_code: int, detail: str, code: str = "APPLICATION_ERROR"):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(AppError):
    """404 Not Found Error."""

    def __init__(self, detail: str = "Tài nguyên không tồn tại"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code="NOT_FOUND")


class ConflictError(AppError):
    """409 Conflict Error."""

    def __init__(self, detail: str = "Tài nguyên đã tồn tại hoặc có xung đột"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, code="CONFLICT")


class ForbiddenError(AppError):
    """403 Forbidden Error."""

    def __init__(self, detail: str = "Không có quyền thực hiện thao tác này"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, code="FORBIDDEN")


class UnauthorizedError(AppError):
    """401 Unauthorized Error."""

    def __init__(self, detail: str = "Chưa đăng nhập hoặc session đã hết hạn"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, code="UNAUTHORIZED")


class ValidationError(AppError):
    """422 Validation Error."""

    def __init__(self, detail: str = "Dữ liệu đầu vào không hợp lệ"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail, code="VALIDATION_ERROR")


class RateLimitError(AppError):
    """429 Rate Limit Exceeded Error."""

    def __init__(self, detail: str = "Gửi quá nhiều yêu cầu. Vui lòng thử lại sau ít phút."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail, code="RATE_LIMIT_EXCEEDED")
