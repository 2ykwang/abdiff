from fastapi import FastAPI

from app.api.routes import users
from app.core.errors import AppError, app_error_handler

app = FastAPI(title="orders-api")
app.add_exception_handler(AppError, app_error_handler)
app.include_router(users.router)
