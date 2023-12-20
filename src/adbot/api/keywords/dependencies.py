from math import ceil
from typing import Annotated, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import and_, select, func

from database import AsyncSession, get_async_session
from models.keyword import KeywordInDB, KeywordCreate, KeywordOutput
from models.user import UserInDB
from models.users_keywords_links import UserKeywordLink
from ..pagination import Pagination, Paginated


async def get_keyword_by_id_dep(
    keyword_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> KeywordInDB:
    keyword = await session.get(KeywordInDB, keyword_id)
    if keyword is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Keyword with id={keyword_id} not found"
        )
    return keyword


async def get_keywords_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    pagination: Annotated[Pagination, Depends()],
    word: Annotated[Optional[str], Query()] = None,
) -> Paginated[KeywordOutput]:
    if word:
        st = select(KeywordInDB).where(KeywordInDB.word == word)
        keyword = await session.scalar(st)
        if keyword:
            keywords = [KeywordOutput.model_validate(keyword)]
        else:
            keywords = []
        res = Paginated(
            total_results=len(keywords), total_pages=1, current_page=1, results=keywords
        )
        return res
    else:
        total_st = select(func.count(KeywordInDB.id))
        total_results = await session.scalar(total_st)
        if total_results is None:
            total_results = 0

        offset = (pagination.page - 1) * pagination.limit
        results_st = select(KeywordInDB).offset(offset).limit(pagination.limit)
        keywords = await session.scalars(results_st)
        res = Paginated(
            total_results=total_results,
            total_pages=max(1, ceil(total_results / pagination.limit)),
            current_page=pagination.page,
            results=[KeywordOutput.model_validate(kw) for kw in keywords.all()]
        )
        return res



async def create_keyword_dep(
    keyword_data: KeywordCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> Tuple[KeywordInDB, bool]:

    # Check whether the keyword already exists
    st = select(KeywordInDB).where(KeywordInDB.word == keyword_data.word)
    keyword = await session.scalar(st)
    if keyword:
        return (keyword, False)

    # Creating the keyword
    keyword = KeywordInDB(
        word=keyword_data.word
    )
    session.add(keyword)
    await session.commit()
    await session.refresh(keyword)
    return (keyword, True)



