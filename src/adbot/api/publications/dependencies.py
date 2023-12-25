from datetime import datetime
from hashlib import md5
from math import ceil
from typing import Annotated, Optional, Tuple, TypeVar

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import Select, delete, select, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import col

from database import AsyncSession, get_async_session
from models.publication import PublicationInDB, PublicationCreate, PublicationOutput
from models.source import SourceInDB
from ..pagination import Pagination, Paginated


async def get_publication_by_id_dep(
    publication_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> PublicationInDB:
    publication = await session.get(PublicationInDB, publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Publication with id={publication_id} not found"
        )
    return publication


StType = TypeVar("StType", bound=Select)

def _apply_get_source_filters(
    st: StType,
    min_dt: Optional[datetime]
) -> StType:
    if min_dt is not None:
        st = st.where(col(PublicationInDB.dt) >= min_dt)
    return st


async def get_last_publications_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    pagination: Annotated[Pagination, Depends()],
    min_dt: Annotated[Optional[datetime], Query()] = None,
) -> Paginated[PublicationOutput]:

    total_st = select(func.count(PublicationInDB.id))
    total_st = _apply_get_source_filters(total_st, min_dt)
    total_results = await session.scalar(total_st)
    if total_results is None:
        total_results = 0

    offset = (pagination.page - 1) * pagination.limit
    results_st = (
        select(PublicationInDB)
            .order_by(col(PublicationInDB.dt).desc())
            .offset(offset).limit(pagination.limit)
    )
    results_st = _apply_get_source_filters(results_st, min_dt)
    publications_res = await session.scalars(results_st)
    res = Paginated(
        total_results=total_results,
        total_pages=max(1, ceil(total_results / pagination.limit)),
        current_page=pagination.page,
        results=[
            PublicationOutput.model_validate(publication)
            for publication in publications_res
        ]
    )
    return res


async def add_publication_dep(
    publication_data: PublicationCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> Tuple[PublicationInDB, bool]:

    # Check whether the source exists
    source = await session.get(SourceInDB, publication_data.source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={publication_data.source_id} not found"
        )        

    # Calculate hash
    hash_base = f"{publication_data.dt.date()}{source.category_id}" \
                                                                f"{publication_data.text}"
    hash_val = md5(
        hash_base.encode('utf-8'), usedforsecurity=False
    ).hexdigest()

    # Check whether the publication hash already exist
    st = select(PublicationInDB).where(col(PublicationInDB.hash) == hash_val)
    duplicate_publication = await session.scalar(st)
    if duplicate_publication:
        return (duplicate_publication, False) # Already exists

    # Create the publication
    publication = PublicationInDB(
        url=publication_data.url,
        hash=hash_val,
        dt=publication_data.dt,
        source_id=publication_data.source_id,
        preview=publication_data.text[:150]
    )
    session.add(publication)
    await session.commit()
    await session.refresh(publication)
    return (publication, True)


async def delete_publication_dep(
    publication_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> bool:
    st = (
        delete(PublicationInDB)
            .where(col(PublicationInDB.id) == publication_id)
            .returning(PublicationInDB)
    )
    res = await session.execute(st)
    await session.commit()

    deleted_cnt = len(res.scalars().all())
    if deleted_cnt == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Publication with id={publication_id} not found"
        )

    return True     # Publication was deleted
    
