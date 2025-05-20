from pydantic import BaseModel, EmailStr, constr
from typing_extensions import Optional


class UserCreateSchema(BaseModel):
    email: EmailStr
    password: constr(max_length=8)
    phone: Optional[str] = None


class UserOutSchema(BaseModel):
    id: int
    email: EmailStr
    phone: Optional[str]
    is_verified: bool

    class Config:
        orm_mode = True


class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    email: Optional[str] = None

