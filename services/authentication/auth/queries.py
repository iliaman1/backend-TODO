from datetime import datetime, timedelta, timezone
from os import environ
from typing import Optional

import jwt
from auth.enums import SortDirection, UserSortBy
from auth.models.models import Permission, Role, User
from auth.schemas import (
    PermissionSchema,
    RoleSchema,
    UserCreateSchema,
    UserUpdateSchema,
)
from fastapi import HTTPException
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

JWT_SECRET_KEY = environ.get("JWT_SECRET_KEY")
ALGORITHM = environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: EmailStr) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreateSchema) -> User:
    if await get_user_by_email(db, user.email):
        return {"details": "This user is registered"}

    db_user = User(
        email=user.email,
        phone=user.phone,
        password_hash=pwd_context.hash(user.password),
        is_verified=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    default_role = await db.execute(select(Role).where(Role.name == "user"))
    default_role = default_role.scalars().first()

    if not default_role:
        default_role = Role(name="user", description="Regular user")
        db.add(default_role)
        await db.commit()
        await db.refresh(default_role)

    db_user.roles.append(default_role)
    await db.commit()
    await db.refresh(db_user)

    return db_user


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    user.password_hash = pwd_context.hash(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, user: User, user_data: UserUpdateSchema
) -> Optional[User]:
    # Check for email uniqueness if it is being changed
    if user_data.email and user_data.email != user.email:
        existing_user = await get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already registered by another user."
            )

    for field, value in user_data.model_dump(exclude_unset=True):
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()


def create_access_token(user: User, expires_delta: Optional[timedelta] = None):
    to_encode = {
        "sub": user.email,
        "user_id": user.id,
        "roles": [role.name for role in user.roles],
    }
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: User, expires_delta: Optional[timedelta] = None):
    to_encode = {
        "sub": user.email,
        "user_id": user.id,
    }
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_verification_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=1))
    to_encode.update({"exp": expire, "type": "email_verification"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire, "type": "password_reset"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def _validate_token(token: str, expected_type: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        required_fields = ["sub", "type", "exp"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(
                    status_code=400, detail=f"Invalid token: missing {field} field"
                )

        if payload["type"] != expected_type:
            raise HTTPException(
                status_code=400, detail=f"Invalid token type. Expected: {expected_type}"
            )

        if datetime.now(timezone.utc).timestamp() > payload["exp"]:
            raise HTTPException(status_code=400, detail="Token has expired")

        return payload

    except jwt.exceptions.PyJWTError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")


def validation_verify_email(token: str):
    return _validate_token(token, "email_verification")


def validate_access_token(token: str):
    return _validate_token(token, "access")


def validate_password_reset_token(token: str):
    return _validate_token(token, "password_reset")


def validate_refresh_token(token: str):
    return _validate_token(token, "refresh")


async def create_role(db: AsyncSession, role: RoleSchema) -> Role:
    db_role = Role(name=role.name, description=role.description)
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role


async def get_roles(db: AsyncSession):
    result = await db.execute(select(Role))
    return result.scalars().all()


async def get_role(db: AsyncSession, role_id: int) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalars().first()


async def update_role(
    db: AsyncSession, role_id: int, role_data: RoleSchema
) -> Optional[Role]:
    db_role = await get_role(db, role_id)
    if db_role:
        db_role.name = role_data.name
        db_role.description = role_data.description
        await db.commit()
        await db.refresh(db_role)
    return db_role


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    db_role = await get_role(db, role_id)
    if db_role:
        await db.delete(db_role)
        await db.commit()
        return True
    return False


async def create_permission(
    db: AsyncSession, permission: PermissionSchema
) -> Permission:
    db_permission = Permission(
        name=permission.name,
        codename=permission.codename,
        description=permission.description,
    )
    db.add(db_permission)
    await db.commit()
    await db.refresh(db_permission)
    return db_permission


async def get_permissions(db: AsyncSession):
    result = await db.execute(select(Permission))
    return result.scalars().all()


async def get_permission(db: AsyncSession, permission_id: int) -> Optional[Permission]:
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    return result.scalars().first()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    sort_by: UserSortBy = UserSortBy.CREATED_AT,
    sort_dir: SortDirection = SortDirection.DESC,
    role_id: Optional[int] = None,
):
    query = select(User)
    count_query = select(func.count(User.id))

    if role_id:
        query = query.join(User.roles).where(Role.id == role_id)
        count_query = count_query.join(User.roles).where(Role.id == role_id)

    if sort_by == UserSortBy.ROLE:
        if not role_id:
            query = query.join(User.roles)
        query = query.order_by(
            Role.name.desc() if sort_dir == SortDirection.DESC else Role.name.asc()
        )
    else:
        sort_column = getattr(User, sort_by.value)
        query = query.order_by(
            sort_column.desc() if sort_dir == SortDirection.DESC else sort_column.asc()
        )

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().unique().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return {"total": total, "users": users}


async def assign_permission_to_role(
    db: AsyncSession, role_id: int, permission_id: int
) -> Optional[Role]:
    role = await get_role(db, role_id)
    permission = await get_permission(db, permission_id)
    if role and permission:
        role.permissions.append(permission)
        await db.commit()
        await db.refresh(role)
    return role


async def remove_permission_from_role(
    db: AsyncSession, role_id: int, permission_id: int
) -> Optional[Role]:
    role = await get_role(db, role_id)
    permission = await get_permission(db, permission_id)
    if role and permission and permission in role.permissions:
        role.permissions.remove(permission)
        await db.commit()
        await db.refresh(role)
    return role
