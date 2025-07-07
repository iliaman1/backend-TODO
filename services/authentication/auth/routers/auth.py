from auth.queries import (
    create_access_token,
    create_refresh_token,
    create_user,
    get_current_user,
    get_user_by_email,
    verify_password,
)
from auth.schemas import UserCreateSchema, UserLoginSchema, UserOutSchema
from core.database import get_session
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register", response_model=UserOutSchema, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user: UserCreateSchema, session: AsyncSession = Depends(get_session)
):
    db_user = await create_user(session, user)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email alredy registered"
        )

    return db_user


@router.post("/login")
async def login(
    credentials: UserLoginSchema,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    db_user = await get_user_by_email(session, credentials.email)
    if not db_user or not verify_password(credentials.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7200,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


async def auth_required(user_id: str = Depends(get_current_user)):
    return user_id
