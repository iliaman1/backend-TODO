from enum import Enum


class UserSortBy(str, Enum):
    CREATED_AT = "created_at"
    EMAIL = "email"
    ROLE = "role"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"
