from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    display_name: str
