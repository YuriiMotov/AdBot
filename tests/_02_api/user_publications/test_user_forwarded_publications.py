from datetime import datetime
import random
from typing import Optional
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from models.publication import PublicationInDB
from freezegun import freeze_time

from tests.helpers import (
    create_publication, create_user, delete_all_objects, get_multipage_results,
    add_user_publications
)

pytestmark = pytest.mark.asyncio(scope="module")


async def test_user_publications_get_one(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """
        Get user's forwarded publications list (one publication)
    """
    user = await create_user(async_session_maker, defaults=True)
    publication = await create_publication(async_client, async_session_maker)
    await add_user_publications(
        async_session_maker,
        user=user,
        publications=[publication]
    )

    resp = await async_client.get(f"/users/{user.uuid}/forwarded-publications/")
    assert resp.status_code == 200
    resp_json = resp.json()
    assert len(resp_json["results"]) == 1
    assert resp_json["results"][0]["id"] == publication["id"]
    assert resp_json["results"][0]["url"] == publication["url"]


@pytest.mark.parametrize(
    "publications_count,limit", [(0, None), (5, None), (5, 2)]
)
async def test_user_publications_get_multipage(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    publications_count: int,
    limit: Optional[int]
):
    """
        Get user's forwarded publications list (variable number of publications)
    """
    user = await create_user(async_session_maker, defaults=True)
    publications = [
        await create_publication(async_client, async_session_maker)
        for _ in range(publications_count)
    ]
    await add_user_publications(
        async_session_maker,
        user=user,
        publications=publications
    )

    url = f"/users/{user.uuid}/forwarded-publications/"
    resp_gen = get_multipage_results(async_client, url, limit=limit)
    publications_res = {publication["id"] async for publication in resp_gen}

    assert len(publications_res) == publications_count


@pytest.mark.parametrize(
    "limit", [None, 1]
)
async def test_user_publications_get_multipage_filtered(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    limit: Optional[int]
):
    """
        Get user's forwarded publications list (multiple publications),
        filtered by `min_id`
    """
    user = await create_user(async_session_maker, defaults=True)
    publications = [
        await create_publication(async_client, async_session_maker)
        for _ in range(3)
    ]
    links = await add_user_publications(
        async_session_maker,
        user=user,
        publications=publications
    )
    links.sort(key=lambda x: x.id)

    url = f"/users/{user.uuid}/forwarded-publications/"
    resp_gen = get_multipage_results(
        async_client,
        url,
        query_params={"min_id": links[1].id},
        limit=limit
    )
    publications_res_ids = [publication["id"] async for publication in resp_gen]

    expected_publication_ids = (links[1].publication_id, links[2].publication_id)
    assert len(publications_res_ids) == 2
    assert publications_res_ids[0] in expected_publication_ids
    assert publications_res_ids[1] in expected_publication_ids


@pytest.mark.parametrize(
    "limit", [None, 1]
)
async def test_user_publications_get_check_order(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    limit: Optional[int]
):
    """
        Get user's forwarded publications list.
        Check whether the results are ordered by `UserPublicationLink.id`.
    """
    user = await create_user(async_session_maker, defaults=True)
    publications = [
        await create_publication(async_client, async_session_maker)
        for _ in range(3)
    ]
    links = await add_user_publications(
        async_session_maker,
        user=user,
        publications=reversed(publications)
    )
    links.sort(key=lambda x: x.id)

    url = f"/users/{user.uuid}/forwarded-publications/"
    resp_gen = get_multipage_results(
        async_client,
        url,
        limit=limit
    )
    publications_res = [publication["id"] async for publication in resp_gen]

    # Make sure that links are ordered by `id` but not by `publication_id`
    assert not (links[0].publication_id < links[1].publication_id < links[2].publication_id)
    assert (links[0].id < links[1].id < links[2].id)

    # Check whether publications are ordered by `link.id` but not by `publication.id`
    assert len(publications_res) == 3
    assert publications_res[0] == links[0].publication_id
    assert publications_res[1] == links[1].publication_id
    assert publications_res[2] == links[2].publication_id


async def test_get_user_publications_user_doesnt_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """ User doesn't exist """

    user_uuid = str(uuid4())

    resp = await async_client.get(f"/users/{user_uuid}/forwarded-publications/")
    assert resp.status_code == 404
    resp_data = resp.json()
    assert resp_data["detail"].find(user_uuid) >= 0

