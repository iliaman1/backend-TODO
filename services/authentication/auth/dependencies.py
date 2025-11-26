from typing import Dict, List, Optional

from auth.models.models import User
from auth.queries import get_user, validate_access_token
from core.database import get_session
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_token_from_header_or_cookie(
    request: Request, token_from_header: Optional[str] = Depends(oauth2_scheme)
) -> str:
    if token_from_header:
        return token_from_header
    token_from_cookie = request.cookies.get("access_token")
    if not token_from_cookie:
        raise HTTPException(
            status_code=401, detail="Authentication credentials were not provided"
        )
    return token_from_cookie


def get_token_payload(token: str = Depends(get_token_from_header_or_cookie)) -> Dict:
    return validate_access_token(token)


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
