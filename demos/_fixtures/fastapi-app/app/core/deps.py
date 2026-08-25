from functools import lru_cache

from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()


def get_user_service() -> UserService:
    return UserService(get_user_repository())
