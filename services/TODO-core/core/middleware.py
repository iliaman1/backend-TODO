import logging

import requests
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger(__name__)


def get_auth_user(request):
    if hasattr(request, "_cached_user"):
        return request._cached_user

    token = request.COOKIES.get("access_token")
    if not token:
        request._cached_user = AnonymousUser()
        return request._cached_user

    try:
        auth_service_url = settings.AUTH_SERVICE_URL
        response = requests.get(
            f"{auth_service_url}/users/me",
            cookies={"access_token": token},
            timeout=5,
        )

        logger.debug(
            f"[Auth] Response from auth service: {response.status_code}, Body: {response.text}"
        )

        if response.status_code == 200:
            payload = response.json()
            user = type(
                "AuthUser",
                (),
                {
                    "is_authenticated": True,
                    "id": payload.get("id"),
                    "email": payload.get("email"),
                    "roles": [
                        role.get("name") for role in payload.get("roles", [])
                    ],  # Extract just the names
                },
            )()
            request._cached_user = user
        else:
            request._cached_user = AnonymousUser()

    except Exception as e:
        logger.error(f"[Auth] Exception during auth: {e}")
        request._cached_user = AnonymousUser()

    return request._cached_user


def jwt_authentication_middleware(get_response):
    def middleware(request):
        request.user = SimpleLazyObject(lambda: get_auth_user(request))
        return get_response(request)

    return middleware
