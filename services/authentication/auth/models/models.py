from core.database import Base, Model
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

user_role_association = Table(
    "user_role_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
    UniqueConstraint("user_id", "role_id", name="uq_user_role"),
)

role_permission_association = Table(
    "role_permission_association",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id")),
    Column("permission_id", Integer, ForeignKey("permissions.id")),
    UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
)


class User(Model):
    __tablename__ = "users"

    email = Column(String(128), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)

    roles = relationship(
        "Role", secondary=user_role_association, back_populates="users", lazy="selectin"
    )
    email_verifications = relationship(
        "EmailVerification", back_populates="user", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_phone", "phone"),
    )


class Role(Model):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    users = relationship(
        "User", secondary=user_role_association, back_populates="roles", lazy="selectin"
    )
    permissions = relationship(
        "Permission",
        secondary=role_permission_association,
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Model):
    __tablename__ = "permissions"

    codename = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    roles = relationship(
        "Role",
        secondary=role_permission_association,
        back_populates="permissions",
        lazy="selectin",
    )


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="email_verifications", lazy="selectin")
