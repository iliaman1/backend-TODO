from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing_extensions import Optional


class UserBaseSchema(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    phone: Optional[str] = Field(
        None, pattern=r"^\+?[1-9]\d{1,14}$", examples=["+1234567890"]
    )


class PasswordSchema(BaseModel):
    password: str = Field(..., min_length=8, max_length=50, examples=["StrongPass123!"])

    @field_validator("password")
    def validate_password(cls, v):
        errors = []
        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("Password must contain at least one digit")
        if not any(c in "!@#$%^&*" for c in v):
            errors.append("Password must contain at least one special character")

        if errors:
            raise ValueError("; ".join(errors))
        return v


class UserCreateSchema(UserBaseSchema, PasswordSchema):
    pass


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = Field(None, examples=["new_user@example.com"])
    phone: Optional[str] = Field(
        None, pattern=r"^\+?[1-9]\d{1,14}$", examples=["+1234567890"]
    )


class PasswordUpdateSchema(PasswordSchema):
    old_password: str


class UserOutSchema(BaseModel):
    id: int = Field(..., examples=[1])
    email: EmailStr = Field(..., examples=["user@example.com"])
    phone: Optional[str] = Field(None, examples=["+1234567890"])
    is_verified: bool = Field(False, examples=[False])
    created_at: datetime = Field(..., examples=["2023-01-01T00:00:00"])

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "phone": "+1234567890",
                "is_verified": False,
                "created_at": "2023-01-01T00:00:00",
            }
        }


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetSchema(PasswordSchema):
    token: str


class PermissionSchema(BaseModel):
    name: str
    codename: str
    description: Optional[str] = None


class PermissionOutSchema(PermissionSchema):
    id: int

    class Config:
        from_attributes = True


class RoleSchema(BaseModel):
    name: str
    description: Optional[str] = None


class RoleOutSchema(RoleSchema):
    id: int
    permissions: list[PermissionOutSchema] = []

    class Config:
        from_attributes = True


class UserListSchema(BaseModel):
    total: int
    users: list[UserOutSchema]
