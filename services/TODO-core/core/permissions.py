from rest_framework.permissions import BasePermission


class IsServiceUser(BasePermission):
    """
    Allows access only to users with the 'service' role.
    """

    def has_permission(self, request, view):
        return request.user and request.user.has_role("service")
