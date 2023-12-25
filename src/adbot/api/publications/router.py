from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, Response

from models.publication import PublicationInDB, PublicationOutput
from .dependencies import (
    add_publication_dep, get_publication_by_id_dep, get_last_publications_dep,
    delete_publication_dep
)
from ..pagination import Paginated


publications_router = APIRouter(
    prefix="/publications",
    tags=["publications"]
)


@publications_router.get("/", response_model=Paginated[PublicationOutput])
async def get_last_publications(
    publications: Annotated[Paginated[PublicationOutput], Depends(get_last_publications_dep)]
):
    """ Get last publications (filter by min_dt) """
    return publications


@publications_router.get(
    "/{publication_id}/",
    response_model=PublicationOutput,
    responses={
        404: {"description": "Publication not found"},
    }
)
async def get_publication(
    publication: Annotated[PublicationInDB, Depends(get_publication_by_id_dep)]
):
    """ Get publication by id """
    return publication


@publications_router.post(
    "/",
    response_model=PublicationOutput,
    status_code=201,
    responses={
        201: {"description": "Publication created"},
        200: {"description": "Publication hash is duplicated. Skip."},
        404: {"description": "Source not forund"},
    }
)
async def add_publication(
    publication_added_tuple: Annotated[Tuple[PublicationInDB, bool], Depends(add_publication_dep)],
    response: Response
):
    """ Add publication """
    if publication_added_tuple[1] == False:     # Publication duplicated.
                                                # Don't add, return existen
        response.status_code = 200
    return publication_added_tuple[0]


@publications_router.delete(
    "/{publication_id}/",
    responses={
        404: {"description": "Publication not found"},
    }
)
async def delete_publication(
    publication_deleted: Annotated[bool, Depends(delete_publication_dep)],
) -> str:
    """ Delete publication """
    return "Publication was deleted"


