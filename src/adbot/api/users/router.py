from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from models.category import CategoryInDB, CategoryOutput
from models.publication import PublicationOutput

from models.user import UserInDB, UserOutput
from models.keyword import KeywordInDB, KeywordOutput
from .dependencies import (
    add_user_keywords_dep, delete_user_keywords_dep, get_user_dep, create_user_dep,
    update_user_dep, get_user_keywords_dep, get_user_forwarded_publications_dep
)
from ..pagination import Paginated


users_router = APIRouter(
    prefix="/users",
    tags=["users"]
)


# `User` endpoints

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


# `User keywords` endpoints

@users_router.get(
    "/{user_uuid}/categories/{category_id}/keywords/",
    response_model=Paginated[KeywordOutput],
    responses={
        404: {"description": "User or category not found"},
    }
)
async def get_user_keywords(
    keywords: Annotated[Paginated[KeywordOutput], Depends(get_user_keywords_dep)]
):
    """ Get user keywords list """
    return keywords


@users_router.post(
    "/{user_uuid}/categories/{category_id}/keywords/",
    responses={
        404: {"description": "User or category not found"},
    }
)
async def add_user_keyword(
    keyword_added: Annotated[Paginated[KeywordOutput], Depends(add_user_keywords_dep)],
) -> str:
    """ Add keyword to user's list """

    if keyword_added:
        return "Keyword added successfully"
    else:
        return "Keyword already in user's list"


@users_router.delete(
    "/{user_uuid}/categories/{category_id}/keywords/",
    responses={
        404: {"description": "User or category not found"},
    }
)
async def delete_user_keyword(
    keyword_deleted: Annotated[
        Paginated[KeywordOutput], Depends(delete_user_keywords_dep)
    ],
) -> str:
    """ Delete keyword from user's list """

    if keyword_deleted:
        return "Keyword deleted successfully"
    else:
        return "Keyword was not in user's list"


# `User's publications` endpoints

@users_router.get("/{user_uuid}/forwarded-publications/")
async def get_user_forwarded_publications(
    publications: Annotated[
        Paginated[PublicationOutput], Depends(get_user_forwarded_publications_dep)
    ]
):
    return publications