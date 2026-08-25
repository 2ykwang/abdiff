from app.core.errors import ConflictError, NotFoundError
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserRead


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def create(self, data: UserCreate) -> UserRead:
        if self._repo.get_by_email(data.email):
            raise ConflictError(f"email already registered: {data.email}")
        return UserRead(**self._repo.add(data.email, data.display_name))

    def get(self, user_id: int) -> UserRead:
        row = self._repo.get(user_id)
        if row is None:
            raise NotFoundError(f"user {user_id} not found")
        return UserRead(**row)
