from auth.dependencies import (
    RoleChecker,
    get_current_user,
    get_token_from_header_or_cookie,
    get_token_payload,
)
from auth.models.models import User
from auth.queries import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    create_user,
    create_verification_token,
    delete_user,
    get_user_by_email,
    update_user,
    update_user_password,
    validate_password_reset_token,
    validate_refresh_token,
    validation_verify_email,
    verify_password,
)
from auth.schemas import (
    PasswordResetRequestSchema,
    PasswordResetSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserOutSchema,
    UserUpdateSchema,
)
from core.database import get_session
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from tasks import send_email, send_password_reset_email

from services.common.kafka_utils import send_kafka_message

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post(
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
    else:
        verification_token = create_verification_token(data={"sub": user.email})
        send_email.delay(token=verification_token)

        # Отправляем сообщение в Kafka
        send_kafka_message(
            "users",
            {
                "event_type": "user_created",
                "user_id": db_user.id,
                "email": db_user.email,
                "created_at": db_user.created_at.isoformat(),
            },
        )

    return db_user


@auth_router.post("/login")
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

    access_token = create_access_token(user=db_user)
    refresh_token = create_refresh_token(user=db_user)

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7200,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@auth_router.get("/token")
async def get_token(request: Request):
    return request.cookies.get("access_token")


@auth_router.get("/users/me", response_model=UserOutSchema)
async def get_current_user_info(user: User = Depends(get_current_user)):
    return user


@auth_router.patch("/users/me", response_model=UserOutSchema)
async def update_current_user(
    user_data: UserUpdateSchema,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await update_user(db, user, user_data)


@auth_router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    await delete_user(db, user)


@auth_router.post("/refresh")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )

    payload = validate_refresh_token(refresh_token)
    user = await get_user_by_email(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    access_token = create_access_token(user=user)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,
    )
    return {"access_token": access_token}


async def auth_required(user: User = Depends(get_current_user)):
    return user


@auth_router.get("/verify-token")
async def verify_token_endpoint(token: str = Depends(get_token_from_header_or_cookie)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    payload = get_token_payload(token)

    return {
        "sub": payload.get("sub"),
        "user_id": payload.get("user_id"),
        "roles": payload.get("roles"),
        "valid": True,
    }


@auth_router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    payload = validation_verify_email(token)
    try:
        user = await get_user_by_email(session, payload["sub"])
        if not user:
            raise HTTPException(
                status_code=404, detail="Пользователь с таким email не найден"
            )

        if user.is_verified:
            return {
                "status": "already_verified",
                "message": "Email уже был подтвержден ранее",
                "email": user.email,
            }

        user.is_verified = True
        await session.commit()

        return {
            "status": "success",
            "message": "Email успешно подтвержден",
            "email": user.email,
            "user_id": user.id,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Ошибка при подтверждении email: {str(e)}"
        )


@auth_router.post("/password-reset-request")
async def password_reset_request(
    reset_request: PasswordResetRequestSchema,
    session: AsyncSession = Depends(get_session),
):
    user = await get_user_by_email(session, reset_request.email)
    if user:
        token = create_password_reset_token(data={"sub": user.email})
        send_password_reset_email.delay(email=user.email, token=token)
    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@auth_router.post("/password-reset")
async def password_reset(
    reset_data: PasswordResetSchema, session: AsyncSession = Depends(get_session)
):
    payload = validate_password_reset_token(reset_data.token)
    user = await get_user_by_email(session, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await update_user_password(session, user, reset_data.password)
    return {"message": "Password has been reset successfully."}


@auth_router.get("/admin/test", dependencies=[Depends(RoleChecker(["admin"]))])
async def admin_test():
    return {"message": "Admin-only endpoint"}
