from pydantic import BaseModel, EmailStr, constr
from typing_extensions import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: constr(max_length=8)
    phone: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    phone: Optional[str]
    is_verified: bool

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenData(BaseModel):
    email: Optional[str] = None

