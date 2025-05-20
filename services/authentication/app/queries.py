from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Role
from auth import get_password_hash
from schemas import UserCreateSchema


def get_user(db: AsyncSession, email: str):
    return db.query(User).filter(User.email== email).first()


def create_user(db: AsyncSession, user: UserCreateSchema):
    db_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    default_role = db.query(Role).filter(Role.name == "user").first()
    if not default_role:
        default_role = Role(name="user", description="Regular user")
        db.add(default_role)
        db.commit()

    db_user.roles.append(default_role)
    db.commit()

    return db_user
