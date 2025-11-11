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
    def roles(self):
        return self.payload.get("roles", [])

    def has_role(self, role):
        return role in self.roles


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
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
        except jwt.PyJWTError:
            raise AuthenticationFailed("Invalid token")

        user = JWTPayloadUser(payload)
        # Используем SimpleLazyObject для отложенного создания объекта
        lazy_user = SimpleLazyObject(lambda: user)
        return (lazy_user, None)
