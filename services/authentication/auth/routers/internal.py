from typing import List

from auth.dependencies import get_current_user
from auth.queries import get_all_users_basic_info, get_users_by_ids
from auth.schemas import UserBasicInfoSchema, UserOutSchema, UsersByIdsSchema
from core.database import get_session
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

internal_router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(get_current_user)],  # Requires any authenticated user
)


@internal_router.post("/users/by_ids", response_model=List[UserOutSchema])
async def get_users_by_ids_endpoint(
    data: UsersByIdsSchema,
    db: AsyncSession = Depends(get_session),
):
    return await get_users_by_ids(db, data.user_ids)


@internal_router.get("/users/all", response_model=List[UserBasicInfoSchema])
async def get_all_users_basic_info_endpoint(
    db: AsyncSession = Depends(get_session),
):
    return await get_all_users_basic_info(db)
