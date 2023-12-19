from typing import Annotated, Optional, Tuple

from fastapi import APIRouter, Depends, Response

from models.keyword import KeywordInDB, KeywordOutput
from .dependencies import get_keywords_dep, get_keyword_by_id_dep, create_keyword_dep
from ..pagination import Paginated



keywords_router = APIRouter(
    prefix="/keywords",
    tags=["keywords"]
)


@keywords_router.get(
    "/",
    response_model=Paginated[KeywordOutput]
)
async def get_keywords(
    keywords: Annotated[KeywordInDB, Depends(get_keywords_dep)]
):
    """ Get keywords by filter """
    return keywords


@keywords_router.get(
    "/{keyword_id}/",
    response_model=KeywordOutput,
    responses={
        404: {"description": "Keyword not found"},
    }
)
async def get_keyword(
    keyword: Annotated[KeywordInDB, Depends(get_keyword_by_id_dep)]
):
    """ Get keyword by id """
    return keyword


@keywords_router.post(
    "/",
    response_model=KeywordOutput,
    status_code=201,
    responses={
        200: {"description": "Keyword already exists"},
        201: {"description": "Keyword created"},
    }
)
async def create_keyword(
    keyword_created_tuple: Annotated[Tuple[KeywordInDB, bool], Depends(create_keyword_dep)],
    response: Response
):
    """ Create keyword or return if already exists """
    if not keyword_created_tuple[1]:
        response.status_code = 200
    return keyword_created_tuple[0]

