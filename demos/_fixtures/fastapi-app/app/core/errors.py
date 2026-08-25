from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})
