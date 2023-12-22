from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, Response

from models.source import SourceInDB, SourceOutput
from .dependencies import (
    create_source_dep, get_source_by_id_dep, get_sources_dep, delete_source_dep,
    update_source_dep
)
from ..pagination import Paginated



sources_router = APIRouter(
    prefix="/sources",
    tags=["sources"]
)


@sources_router.get("/", response_model=Paginated[SourceOutput])
async def get_sources(
    sources: Annotated[Paginated[SourceOutput], Depends(get_sources_dep)]
):
    """ Get sources by filter (source_type) """
    return sources


@sources_router.get(
    "/{source_id}/",
    response_model=SourceOutput,
    responses={
        404: {"description": "Source not found"},
    }
)
async def get_source(
    source: Annotated[SourceInDB, Depends(get_source_by_id_dep)]
):
    """ Get source by id """
    return source


@sources_router.post(
    "/",
    response_model=SourceOutput,
    status_code=201,
    responses={
        201: {"description": "Source created"},
        400: {"description": "Source title or source info are duplicated"},
    }
)
async def create_source(
    source: Annotated[SourceInDB, Depends(create_source_dep)],
):
    """ Create source """
    return source


@sources_router.patch(
    "/{source_id}/",
    response_model=SourceOutput,
    status_code=201,
    responses={
        400: {"description": "Source title or source info are duplicated"},
    }
)
async def update_source(
    source: Annotated[SourceInDB, Depends(update_source_dep)],
):
    """ Update source """
    return source



@sources_router.delete(
    "/{source_id}/",
    responses={
        404: {"description": "Source not found"},
    }
)
async def delete_source(
    source_deleted: Annotated[bool, Depends(delete_source_dep)],
) -> str:
    """ Delete source """
    return "Source was deleted"
