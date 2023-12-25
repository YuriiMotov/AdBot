from datetime import datetime
import random
from typing import Optional
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from models.publication import PublicationInDB
from freezegun import freeze_time

from tests.helpers import create_publication, delete_all_objects, get_multipage_results

pytestmark = pytest.mark.asyncio(scope="module")


async def test_publications_get_last_without_filter(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """
        Get last publications without filters.
    """
    await delete_all_objects(async_session_maker, PublicationInDB)
    publication = await create_publication(async_client, async_session_maker)
    
    resp = await async_client.get(f"/publications/")
    assert resp.status_code == 200
    publications_data = resp.json()
    assert len(publications_data["results"]) == 1
    publication_data = publications_data["results"][0]
    assert len(publication_data) == 7 # Make sure we check all response model fields
    assert publication_data["url"] == publication["url"]
    assert publication_data["id"] == publication["id"]
    assert publication_data["source_id"] == publication["source_id"]
    assert publication_data["dt"] == publication["dt"]
    assert publication_data["hash"] == publication["hash"]
    assert publication_data["preview"] == publication["preview"]
    assert publication_data["processed"] == publication["processed"]


@pytest.mark.parametrize(
    "publications_count,limit",
    [(5, None), (2, 2), (5, 2)]
)
async def test_publications_get_last_without_filter_mulipage(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    publications_count: int,
    limit: Optional[int]
):
    """
        Get last publications without filters.
        Check whether it works with different results count and limit per page
    """

    await delete_all_objects(async_session_maker, PublicationInDB)
    publications = [
        await create_publication(async_client, async_session_maker)
        for _ in range(publications_count)
    ]
    publication_ids = {publication["id"] for publication in publications}
    
    results_gen = get_multipage_results(
        async_client, base_url="/publications/", limit=limit
    )
    res_publication_ids = {publication["id"] async for publication in results_gen}
    assert publication_ids == res_publication_ids


async def test_publications_get_last_check_order(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """
        Get last publications without filters.
        Results should be ordered by `dt` descend (newest first)
    """
    await delete_all_objects(async_session_maker, PublicationInDB)
    with freeze_time("2030-01-01"):
        publication_newest = await create_publication(async_client, async_session_maker)
    with freeze_time("2000-01-01"):
        publication_oldest = await create_publication(async_client, async_session_maker)
    with freeze_time("2020-01-01"):
        publication_middle = await create_publication(async_client, async_session_maker)
    publication_ids_ordered = [
        publication_newest["id"],
        publication_middle["id"],
        publication_oldest["id"]
    ]

    results_gen = get_multipage_results(
        async_client, base_url="/publications/"
    )
    res_publication_ids_list = [publication["id"] async for publication in results_gen]
    assert len(res_publication_ids_list) == len(publication_ids_ordered)
    assert res_publication_ids_list[0] == publication_ids_ordered[0]
    assert res_publication_ids_list[1] == publication_ids_ordered[1]
    assert res_publication_ids_list[2] == publication_ids_ordered[2]



async def test_publications_get_last_filter_by_dt(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """
        Get last publications filtered by min_dt.
    """
    await delete_all_objects(async_session_maker, PublicationInDB)
    with freeze_time("2030-01-01"):
        publication_newest = await create_publication(async_client, async_session_maker)
    with freeze_time("2000-01-01"):
        publication_oldest = await create_publication(async_client, async_session_maker)
    with freeze_time("2020-01-01"):
        publication_middle = await create_publication(async_client, async_session_maker)
    publication_expected_ids_ordered = [
        publication_newest["id"],
        publication_middle["id"]
    ]

    min_dt = datetime(year=2020, month=1, day=1)

    results_gen = get_multipage_results(
        async_client,
        base_url="/publications/",
        query_params={"min_dt": min_dt}
    )
    res_publication_ids_list = [publication["id"] async for publication in results_gen]
    assert len(res_publication_ids_list) == len(publication_expected_ids_ordered)
    assert res_publication_ids_list[0] == publication_expected_ids_ordered[0]
    assert res_publication_ids_list[1] == publication_expected_ids_ordered[1]


