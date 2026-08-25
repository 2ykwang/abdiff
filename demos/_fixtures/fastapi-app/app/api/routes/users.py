from fastapi import APIRouter, Depends, status

from app.core.deps import get_user_service
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, service: UserService = Depends(get_user_service)) -> UserRead:
    return service.create(data)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, service: UserService = Depends(get_user_service)) -> UserRead:
    return service.get(user_id)
