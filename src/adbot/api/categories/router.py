from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, Response

from models.category import CategoryInDB, CategoryOutput
from .dependencies import delete_category_dep, get_category_by_id_dep, create_category_dep, get_categories_dep
from ..pagination import Paginated



categories_router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


@categories_router.get(
    "/",
    response_model=Paginated[CategoryOutput]
)
async def get_categories(
    categories: Annotated[Paginated[CategoryOutput], Depends(get_categories_dep)]
):
    """ Get categories by filter """
    return categories


@categories_router.get(
    "/{category_id}/",
    response_model=CategoryOutput,
    responses={
        404: {"description": "Category not found"},
    }
)
async def get_category(
    category: Annotated[CategoryInDB, Depends(get_category_by_id_dep)]
):
    """ Get category by id """
    return category


@categories_router.post(
    "/",
    response_model=CategoryOutput,
    status_code=201,
    responses={
        200: {"description": "Category already exists"},
        201: {"description": "Category created"},
    }
)
async def create_category(
    category_created_tuple: Annotated[
        Tuple[CategoryInDB, bool], Depends(create_category_dep)
    ],
    response: Response
):
    """ Create category or return if already exists """
    if not category_created_tuple[1]:
        response.status_code = 200
    return category_created_tuple[0]


@categories_router.delete(
    "/{category_id}/",
    responses={
        404: {"description": "Category not found"},
    }
)
async def delete_category(
    category_deleted: Annotated[bool, Depends(delete_category_dep)],
) -> str:
    """ Delete category """
    return "Category was deleted"
