from auth.dependencies import RoleChecker, get_current_user
from auth.models.models import User
from auth.queries import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    create_user,
    create_verification_token,
    get_user_by_email,
    update_user_password,
    validate_password_reset_token,
    validation_verify_email,
    verify_password,
)
from auth.schemas import (
    PasswordResetRequestSchema,
    PasswordResetSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserOutSchema,
)
from core.database import get_session
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from tasks import send_email, send_password_reset_email

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
    else:
        verification_token = create_verification_token(data={"sub": user.email})
        send_email.delay(token=verification_token)

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


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


async def auth_required(user: User = Depends(get_current_user)):
    return user


@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    payload = validation_verify_email(token)
    print(payload["sub"])
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


@router.post("/password-reset-request")
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


@router.post("/password-reset")
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


@router.get("/admin/test", dependencies=[Depends(RoleChecker(["admin"]))])
async def admin_test():
    return {"message": "Admin-only endpoint"}
