from typing import Annotated

from fastapi import APIRouter, Depends

from models.user import UserInDB, UserOutput
from .dependencies import get_user_dep, create_user_dep, update_user_dep



users_router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@users_router.get(
    "/{user_uuid}/",
    response_model=UserOutput,
    responses={
        404: {"description": "User not found"},
    }
)
async def get_user(
    user: Annotated[UserInDB, Depends(get_user_dep)]
):
    """ Get user data by uuid """
    return user


@users_router.post(
    "/{user_uuid}/",
    response_model=UserOutput,
    status_code=201,
    responses={
        201: {"description": "User created"},
        400: {"description": "Uuid, name or telegram ID is already in use"},
    }
)
async def create_user(
    user: Annotated[UserInDB, Depends(create_user_dep)],
):
    """ Create new user """
    return user



@users_router.patch(
    "/{user_uuid}/",
    response_model=UserOutput,
    responses={
        400: {"description": "Name or telegram ID is already in use"},
        404: {"description": "User not found"},
    }
)
async def update_user(
    user: Annotated[UserInDB, Depends(update_user_dep)],
):
    """ Update user data """
    return user

