from typing import TypeVar
from math import ceil
from typing import Annotated, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, Select, delete, or_, select, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import col
from common_types import SourceType

from database import AsyncSession, get_async_session
from models.category import CategoryInDB
from models.source import SourceInDB, SourceCreate, SourceOutput, SourcePatch
from ..pagination import Pagination, Paginated


async def get_source_by_id_dep(
    source_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> SourceInDB:
    source = await session.get(SourceInDB, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={source_id} not found"
        )
    return source


StType = TypeVar("StType", bound=Select)

def _apply_get_source_filters(
    st: StType,
    source_type: Optional[SourceType],
    category_id: Optional[int],
) -> StType:
    if source_type is not None:
        st = st.where(col(SourceInDB.type) == source_type)
    if category_id is not None:
        st = st.where(col(SourceInDB.category_id) == category_id)
    return st


async def get_sources_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    pagination: Annotated[Pagination, Depends()],
    source_type: Annotated[Optional[SourceType], Query()] = None,
    category_id: Annotated[Optional[int], Query()] = None,
) -> Paginated[SourceOutput]:

    total_st = select(func.count(SourceInDB.id))
    total_st = _apply_get_source_filters(total_st, source_type, category_id)
    total_results = await session.scalar(total_st)
    if total_results is None:
        total_results = 0

    offset = (pagination.page - 1) * pagination.limit
    results_st = select(SourceInDB).offset(offset).limit(pagination.limit)
    results_st = _apply_get_source_filters(results_st, source_type, category_id)
    sources = await session.scalars(results_st)
    res = Paginated(
        total_results=total_results,
        total_pages=max(1, ceil(total_results / pagination.limit)),
        current_page=pagination.page,
        results=[SourceOutput.model_validate(source) for source in sources.all()]
    )
    return res



async def create_source_dep(
    source_data: SourceCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> SourceInDB:

    # Check whether the category exists
    category = await session.get(CategoryInDB, source_data.category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id={source_data.category_id} not found"
        )        

    # Check whether the source title or info already exist
    st = select(SourceInDB).where(
        or_(
            col(SourceInDB.title) == source_data.title,
            col(SourceInDB.source_info) == source_data.source_info,
        )
    )
    sources = (await session.scalars(st)).all()
    if sources:
        errors = []
        for source in sources:
            if source.title == source_data.title:
                errors.append({"code": 'SOURCE_TITLE_ALREADY_EXISTS'})
            if source.source_info == source_data.source_info:
                errors.append({"code": 'SOURCE_INFO_ALREADY_EXISTS'})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )

    # Create the source
    source = SourceInDB(
        title=source_data.title,
        type=source_data.type,
        source_info=source_data.source_info,
        category_id=source_data.category_id
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def update_source_dep(
    source_id: int,
    source_data: SourcePatch,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> SourceInDB:

    # Check whether the category exists
    if source_data.category_id is not None:
        category = await session.get(CategoryInDB, source_data.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id={source_data.category_id} not found"
            )        

    # Check whether the source already exists
    update_data = source_data.model_dump(exclude_unset=True)
    conditions: list[ColumnElement[bool]] = []
    if "title" in update_data.keys():
        conditions.append(col(SourceInDB.title) == source_data.title)
    if "source_info" in update_data.keys():
        conditions.append(col(SourceInDB.source_info) == source_data.source_info)
    st = select(SourceInDB).where(or_(False, *conditions))
    
    sources = (await session.scalars(st)).all()
    if sources:
        errors = []
        for source in sources:
            if source.title == source_data.title:
                errors.append({"code": 'SOURCE_TITLE_ALREADY_EXISTS'})
            if source.source_info == source_data.source_info:
                errors.append({"code": 'SOURCE_INFO_ALREADY_EXISTS'})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )

    # Update the source
    source_to_update = await session.get(SourceInDB, source_id)
    if source_to_update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={source_id} not found"
        )
    for attr, value in update_data.items():
        setattr(source_to_update, attr, value)
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured. Try again"
        )
    return source_to_update


async def delete_source_dep(
    source_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> bool:

    st = delete(SourceInDB).where(col(SourceInDB.id) == source_id)
    res = await session.execute(st)
    await session.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Source with id={source_id} not found"
        )

    return True     # Source was deleted
    
