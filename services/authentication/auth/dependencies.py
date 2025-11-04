from typing import Dict, List

import jwt
from auth.models.models import User
from auth.queries import ALGORITHM, SECRET_KEY, get_user
from core.database import get_session
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession


def get_token_payload(request: Request) -> Dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_session),
) -> User:
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=403, detail="User inactive")

    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, payload: dict = Depends(get_token_payload)):
        user_roles = payload.get("roles", [])
        if not any(role in self.allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have the required roles. Required roles: {self.allowed_roles}",
            )
        return payload
