from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str = "Internal application error",
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        content: dict[str, Any] = {
            "error": True,
            "detail": detail,
        }
        if code:
            content["code"] = code
        if extra:
            content["extra"] = extra
        super().__init__(status_code=status_code, detail=content)


class NotFoundException(AppException):
    def __init__(self, entity: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} not found",
            code="NOT_FOUND",
        )


class DuplicateException(AppException):
    def __init__(self, entity: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity} already exists",
            code="DUPLICATE",
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="FORBIDDEN",
        )


class ValidationException(AppException):
    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR",
        )


class BusinessRuleError(HTTPException):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": code,
                "message": message,
                "details": self.details,
            },
        )


class SyncConflictError(HTTPException):
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = "SYNC_CONFLICT"
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": self.code,
                "message": message,
                "details": {**self.details, "options": ["override", "skip"]},
            },
        )


class DBConstraintError(HTTPException):
    def __init__(
        self,
        code: str = "DB_CONSTRAINT",
        message: str = "Error de restricción de base de datos",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": code,
                "message": message,
                "details": self.details,
            },
        )
