from math import ceil
from typing import Annotated, Optional, Sequence, Tuple
from uuid import UUID 

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, insert, select, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col
from adbot.api.categories.dependencies import get_category_by_id_dep
from adbot.api.keywords.dependencies import create_keyword_dep
from adbot.api.pagination import Paginated, Pagination

from database import AsyncSession, get_async_session
from models.category import CategoryInDB
from models.keyword import KeywordCreate, KeywordInDB, KeywordOutput
from models.user import UserInDB, UserCreate, UserPatch
from models.users_keywords_links import UserKeywordLink


async def get_user_dep(
    user_uuid: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> UserInDB:
    user = await session.get(UserInDB, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with uuid={user_uuid} not found"
        )
    return user


async def create_user_dep(
    user_uuid: UUID,
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> UserInDB:

    # Checking whether `uuid`, `name` or `telegram_id' is already used
    conditions = [
        col(UserInDB.uuid) == user_uuid,
        col(UserInDB.name) == user_data.name
    ]
    if user_data.telegram_id is not None:
        conditions.append(col(UserInDB.telegram_id) == user_data.telegram_id)

    st = select(UserInDB).where(or_(False, *conditions))
    users = (await session.scalars(st)).all()
    if users:
        errors = []
        for user in users:
            if user.uuid == user_uuid:
                errors.append({"code": 'DUPLICATE_UUID'})
            if user.name == user_data.name:
                errors.append({"code": 'USER_NAME_ALREADY_USED'})
            if user_data.telegram_id is not None:
                if user.telegram_id == user_data.telegram_id:
                    errors.append({"code": 'TELEGRAM_ID_ALREADY_USED'})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )

    # Creating the user
    user = UserInDB(
        uuid=user_uuid,
        **user_data.model_dump()
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as e:
        e.args
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured. Try again"
        )
    return user


async def update_user_dep(
    user_uuid: UUID,
    user_data: UserPatch,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> UserInDB:
    
    # Checking whether the `name` or `telegram_id' is already used by other users
    update_data = user_data.model_dump(exclude_unset=True)
    conditions = []
    if "name" in update_data.keys():
        conditions.append(col(UserInDB.name) == user_data.name)
    if "telegram_id" in update_data.keys():
        if user_data.telegram_id is not None:
            conditions.append(col(UserInDB.telegram_id) == user_data.telegram_id)
    if conditions:
        st = select(UserInDB).where(col(UserInDB.uuid) != user_uuid).where(or_(*conditions))
        users: Sequence[UserInDB] = (await session.scalars(st)).all()
        if users:
            errors = []
            for user in users:
                if user.name == user_data.name:
                    errors.append({"code": 'USER_NAME_ALREADY_USED'})
                if user_data.telegram_id is not None:
                    if user.telegram_id == user_data.telegram_id:
                        errors.append({"code": 'TELEGRAM_ID_ALREADY_USED'})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": errors}
            )

    # Updating user data
    user_to_update: Optional[UserInDB] = await session.get(UserInDB, user_uuid)
    if user_to_update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with uuid={user_uuid} not found"
        )
    if len(update_data) == 0:   # Nothing to update
        return user_to_update
    
    for attr, value in update_data.items():
        setattr(user_to_update, attr, value)
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured. Try again"
        )
    return user_to_update


def _construct_keywords_by_user_st(
    is_total_st: bool, user_uuid: UUID, category_id: int, pagination: Pagination
):
    if is_total_st:
        st = select(func.count(KeywordInDB.id)).group_by(UserKeywordLink.user_uuid)
    else:
        offset = (pagination.page - 1) * pagination.limit
        st = select(KeywordInDB).offset(offset).limit(pagination.limit)
    st = (
        st.select_from(UserKeywordLink)
            .join(KeywordInDB)
            .where(
                and_(
                    UserKeywordLink.user_uuid == user_uuid,
                    UserKeywordLink.category_id == category_id
                )
            )
    )
    return st


async def get_user_keywords_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    pagination: Annotated[Pagination, Depends()],
    user_uuid: UUID,
    category_id: int
) -> Paginated[KeywordOutput]:

    total_st = _construct_keywords_by_user_st(
        is_total_st=True,
        user_uuid=user_uuid,
        category_id=category_id,
        pagination=pagination
    )
    total_results = await session.scalar(total_st)
    if total_results is None:
        total_results = 0

    results_st = _construct_keywords_by_user_st(
        is_total_st=False,
        user_uuid=user_uuid,
        category_id=category_id,
        pagination=pagination
    )
    keywords = await session.scalars(results_st)
    res = Paginated(
        total_results=total_results,
        total_pages=max(1, ceil(total_results / pagination.limit)),
        current_page=pagination.page,
        results=[KeywordOutput.model_validate(kw) for kw in keywords.all()]
    )
    return res


async def add_user_keywords_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[UserInDB, Depends(get_user_dep)],
    category: Annotated[CategoryInDB, Depends(get_category_by_id_dep)],
    word: Annotated[str, Query()],
) -> bool:
    keyword_created_tuple = await create_keyword_dep(
        session=session,
        keyword_data=KeywordCreate(word=word)
    )
    keyword = keyword_created_tuple[0]

    try:
        await session.execute(
            insert(UserKeywordLink),
            [
                {
                    "user_uuid": user.uuid,
                    "keyword_id": keyword.id,
                    "category_id": category.id
                }
            ]
        )
        await session.commit()
    except IntegrityError as e:
        return False  # Already in user's list

    return True    # Added to user's list


async def delete_user_keywords_dep(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[UserInDB, Depends(get_user_dep)],
    category: Annotated[CategoryInDB, Depends(get_category_by_id_dep)],
    word: Annotated[str, Query()],
) -> bool:
    
    st = select(KeywordInDB).where(KeywordInDB.word == word)
    keyword = await session.scalar(st)
    if keyword is None:
        return False    # Already not in user's list (not even exists)

    st = delete(UserKeywordLink).where(
        and_(
            UserKeywordLink.user_uuid == user.uuid,
            UserKeywordLink.category_id == category.id,
            UserKeywordLink.keyword_id == keyword.id
        )
    ).returning(UserKeywordLink)
    res = await session.execute(st)
    await session.commit()

    deleted_cnt = len(res.scalars().all())
    if deleted_cnt == 0:
        return False  # Already not in user's list

    return True    # Deleted from user's list
