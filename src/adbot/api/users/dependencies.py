from typing import Annotated
from uuid import UUID 

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

from database import AsyncSession, get_async_session
from models.user import UserInDB, UserCreate, UserPatch


async def get_user_dep(
    user_uuid: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> UserInDB:

    HTTPException(400, "dfgxfdgsfg")
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
        UserInDB.uuid == user_uuid,
        UserInDB.name == user_data.name
    ]
    if user_data.telegram_id is not None:
        conditions.append(UserInDB.telegram_id == user_data.telegram_id)

    st = select(UserInDB).where(or_(*conditions))
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
        conditions.append(UserInDB.name == user_data.name)
    if "telegram_id" in update_data.keys():
        if user_data.telegram_id is not None:
            conditions.append(UserInDB.telegram_id == user_data.telegram_id)
    if conditions:
        st = select(UserInDB).where(UserInDB.uuid != user_uuid).where(or_(*conditions))
        users = (await session.scalars(st)).all()
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
    user = await session.get(UserInDB, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with uuid={user_uuid} not found"
        )
    if len(update_data) == 0:   # Nothing to update
        return user
    
    for attr, value in update_data.items():
        setattr(user, attr, value)
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured. Try again"
        )
    return user
