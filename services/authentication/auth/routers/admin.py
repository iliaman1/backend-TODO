from typing import List

from auth.dependencies import RoleChecker
from auth.enums import SortDirection, UserSortBy
from auth.queries import (
    assign_permission_to_role,
    create_permission,
    create_role,
    delete_role,
    get_permissions,
    get_role,
    get_roles,
    get_users,
    remove_permission_from_role,
    update_role,
)
from auth.schemas import (
    PermissionOutSchema,
    PermissionSchema,
    RoleOutSchema,
    RoleSchema,
    UserListSchema,
)
from core.database import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(RoleChecker(["admin"]))],
)


@admin_router.post(
    "/roles", response_model=RoleOutSchema, status_code=status.HTTP_201_CREATED
)
async def add_role(role: RoleSchema, db: AsyncSession = Depends(get_session)):
    return await create_role(db, role)


@admin_router.get("/roles", response_model=List[RoleOutSchema])
async def list_roles(db: AsyncSession = Depends(get_session)):
    return await get_roles(db)


@admin_router.get("/roles/{role_id}", response_model=RoleOutSchema)
async def retrieve_role(role_id: int, db: AsyncSession = Depends(get_session)):
    db_role = await get_role(db, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@admin_router.put("/roles/{role_id}", response_model=RoleOutSchema)
async def edit_role(
    role_id: int, role: RoleSchema, db: AsyncSession = Depends(get_session)
):
    db_role = await update_role(db, role_id, role)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@admin_router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(role_id: int, db: AsyncSession = Depends(get_session)):
    if not await delete_role(db, role_id):
        raise HTTPException(status_code=404, detail="Role not found")


@admin_router.post(
    "/permissions",
    response_model=PermissionOutSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_permission(
    permission: PermissionSchema, db: AsyncSession = Depends(get_session)
):
    return await create_permission(db, permission)


@admin_router.get("/permissions", response_model=List[PermissionOutSchema])
async def list_permissions(db: AsyncSession = Depends(get_session)):
    return await get_permissions(db)


@admin_router.get("/users", response_model=UserListSchema)
async def list_users(
    db: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 10,
    sort_by: UserSortBy = UserSortBy.CREATED_AT,
    sort_dir: SortDirection = SortDirection.DESC,
):
    return await get_users(db, skip, limit, sort_by, sort_dir)


@admin_router.post(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RoleOutSchema,
)
async def add_permission_to_role(
    role_id: int, permission_id: int, db: AsyncSession = Depends(get_session)
):
    role = await assign_permission_to_role(db, role_id, permission_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role or Permission not found")
    return role


@admin_router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RoleOutSchema,
)
async def revoke_permission_from_role(
    role_id: int, permission_id: int, db: AsyncSession = Depends(get_session)
):
    role = await remove_permission_from_role(db, role_id, permission_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role or Permission not found, or permission not assigned",
        )
    return role
