import jwt
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTPayloadUser:
    def __init__(self, payload):
        self.payload = payload
        self.is_authenticated = True

    @property
    def id(self):
        return self.payload.get("user_id")

    @property
    def email(self):
        return self.payload.get("sub")

    @property
    def roles(self):
        return self.payload.get("roles", [])

    def has_role(self, role):
        return role in self.roles


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Пытаемся получить токен из заголовка Authorization
        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header:
            try:
                # Ожидаем заголовок в формате "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                # Если формат неправильный, игнорируем
                pass

        # Если в заголовке нет, ищем в cookie
        if not token:
            token = request.COOKIES.get("access_token")

        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired")
        except jwt.PyJWTError as e:
            raise AuthenticationFailed(f"Invalid token: {e}")

        user = JWTPayloadUser(payload)
        # Используем SimpleLazyObject для отложенного создания объекта
        lazy_user = SimpleLazyObject(lambda: user)
        return (lazy_user, None)
