from math import ceil
from typing import Annotated, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select, func
from sqlmodel import col

from database import AsyncSession, get_async_session
from models.category import CategoryInDB, CategoryCreate, CategoryOutput
from ..pagination import Pagination, Paginated


async def get_category_by_id_dep(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> CategoryInDB:
    category = await session.get(CategoryInDB, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id={category_id} not found"
        )
    return category


async def get_categories_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    pagination: Annotated[Pagination, Depends()],
    name: Annotated[Optional[str], Query()] = None,
) -> Paginated[CategoryOutput]:
    if name:
        st = select(CategoryInDB).where(col(CategoryInDB.name) == name)
        category = await session.scalar(st)
        if category:
            categories = [CategoryOutput.model_validate(category)]
        else:
            categories = []
        res = Paginated(
            total_results=len(categories), total_pages=1, current_page=1, results=categories
        )
        return res
    else:
        total_st = select(func.count(CategoryInDB.id))
        total_results = await session.scalar(total_st)
        if total_results is None:
            total_results = 0

        offset = (pagination.page - 1) * pagination.limit
        results_st = select(CategoryInDB).offset(offset).limit(pagination.limit)
        categories_res = await session.scalars(results_st)
        res = Paginated(
            total_results=total_results,
            total_pages=max(1, ceil(total_results / pagination.limit)),
            current_page=pagination.page,
            results=[CategoryOutput.model_validate(cat) for cat in categories_res]
        )
        return res



async def create_category_dep(
    category_data: CategoryCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> Tuple[CategoryInDB, bool]:

    # Check whether the category already exists
    st = select(CategoryInDB).where(col(CategoryInDB.name) == category_data.name)
    category = await session.scalar(st)
    if category:
        return (category, False)

    # Creating the category
    category = CategoryInDB(
        name=category_data.name
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return (category, True)


async def delete_category_dep(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> bool:

    st = delete(CategoryInDB).where(col(CategoryInDB.id) == category_id)
    res = await session.execute(st)
    await session.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Category with id={category_id} not found"
        )

    return True     # Category was deleted
    
