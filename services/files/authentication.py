import jwt
from os import getenv
from fastapi import Request, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

# Загружаем секретный ключ и алгоритм из переменных окружения
# Убедитесь, что они есть в .env файле для files-api
JWT_SECRET_KEY = getenv("JWT_SECRET_KEY")
ALGORITHM = getenv("JWT_ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class JWTPayloadUser:
    """
    Класс-заглушка для пользователя, основанный на данных из JWT токена.
    """

    def __init__(self, payload: dict):
        self.payload = payload
        self.is_authenticated = True

    @property
    def id(self) -> int:
        return self.payload.get("user_id")

    @property
    def email(self) -> str:
        return self.payload.get("sub")

    @property
    def roles(self) -> list:
        return self.payload.get("roles", [])

    def has_role(self, role: str) -> bool:
        return role in self.roles


def get_token_from_header_or_cookie(
    request: Request, token_from_header: str = Depends(oauth2_scheme)
) -> str:
    """
    Извлекает токен либо из заголовка Authorization, либо из cookie.
    """
    if token_from_header:
        return token_from_header

    token_from_cookie = request.cookies.get("access_token")
    if not token_from_cookie:
        raise HTTPException(
            status_code=401, detail="Authentication credentials were not provided"
        )
    return token_from_cookie


def get_current_user(
    token: str = Depends(get_token_from_header_or_cookie),
) -> JWTPayloadUser:
    """
    Декодирует токен и возвращает объект JWTPayloadUser.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    return JWTPayloadUser(payload)
