from math import ceil
from typing import Optional
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from common_types import SourceType

from tests.helpers import (
    ResStat, create_categories_list, create_sources_list, delete_all_sources, #get_sources_count_by_filter,
    get_multipage_results, #delete_all_sources
)

pytestmark = pytest.mark.asyncio(scope="module")


async def test_sources_get_by_filter_empty_table(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Get all sources, but no one exists in the DB """
    await delete_all_sources(async_session_maker)

    sources_res = get_multipage_results(async_client, f"/sources/")
    res_sources_set = {source["title"] async for source in sources_res}

    assert len(res_sources_set) == 0


async def test_sources_get_by_filter_without_filters(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Get all sources. There are sources of 2 types in 2 categories """
    categories = await create_categories_list(async_session_maker, count=2)
    sources = await create_sources_list(
        async_session_maker,
        count=5,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    sources.extend(
        await create_sources_list(
            async_session_maker,
            count=5,
            source_type=SourceType.facebook,
            category_id=categories[1].id
        )
    )

    sources_res = get_multipage_results(async_client, f"/sources/")
    res_sources_set = {source["title"] async for source in sources_res}
    actual_sources_set = {source.title for source in sources}

    assert res_sources_set == actual_sources_set




async def test_sources_get_by_filter_empty_res(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Get sources by filter. Empty result, bu there are other sources in the DB """
    categories = await create_categories_list(async_session_maker, count=1)

    url = f"/sources/?source_type={SourceType.facebook}&category_id={categories[0].id}"
    sources_res = get_multipage_results(async_client, url)
    res_sources_set = {source["title"] async for source in sources_res}

    assert len(res_sources_set) == 0


@pytest.mark.parametrize(
    "count_in_groups_1_3,limit,source_type",
    [
        (5, None, None),
        (30, None, None),
        (5, None, SourceType.telegram),
        (30, None, SourceType.telegram),
        (5, 1, SourceType.telegram),
        (30, 100, SourceType.telegram),
    ]
)
async def test_sources_get_by_sourcetype_multipage(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    count_in_groups_1_3: int,
    limit: Optional[int],
    source_type: Optional[SourceType]
):
    """
        Request sources by filter (`source_type`).
        Requests with different `limit` parameter.
    """
    COUNT_IN_GROUP_2 = 1
    await delete_all_sources(async_session_maker)
    categories = await create_categories_list(async_session_maker, count=2)
    sources_1 = await create_sources_list(
        async_session_maker,
        count=count_in_groups_1_3,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    sources_2 = await create_sources_list(
            async_session_maker,
            count=COUNT_IN_GROUP_2,
            source_type=SourceType.facebook,
            category_id=categories[1].id
        )
    sources_3 = await create_sources_list(
        async_session_maker,
        count=count_in_groups_1_3,
        source_type=SourceType.telegram,
        category_id=categories[1].id
    )
    sources_4 = await create_sources_list(
            async_session_maker,
            count=COUNT_IN_GROUP_2,
            source_type=SourceType.facebook,
            category_id=categories[0].id
        )

    expected_total = (count_in_groups_1_3 + COUNT_IN_GROUP_2) * 2
    base_url = "/sources/"
    if source_type:
        base_url = f"{base_url}?source_type={source_type}"
        expected_total = count_in_groups_1_3 * 2

    resp_stat = ResStat()
    sources_results = get_multipage_results(
        async_client=async_client,
        base_url=base_url,
        resp_stat=resp_stat,
        limit=limit
    )
    unique_titles = {source["title"] async for source in sources_results}
    
    assert len(unique_titles) == expected_total
    if limit:
        expected_pages = ceil(expected_total / limit)
        assert resp_stat.total_pages == expected_pages, "Check number of pages"


@pytest.mark.parametrize(
    "count_in_groups_1_3,limit,category_index",
    [
        (5, None, None),
        (30, None, None),
        (5, None, 0),
        (30, None, 0),
        (5, None, 1),
        (30, None, 1),
        (5, 1, 0),
        (30, 100, 0),
    ]
)
async def test_sources_get_by_category_multipage(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    count_in_groups_1_3: int,
    limit: Optional[int],
    category_index: Optional[int]
):
    """
        Request sources by filter (`category_id`).
        Requests with different `limit` parameter.
    """
    COUNT_IN_GROUP_2 = 1
    await delete_all_sources(async_session_maker)
    categories = await create_categories_list(async_session_maker, count=2)
    sources_1 = await create_sources_list(
        async_session_maker,
        count=count_in_groups_1_3,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    sources_2 = await create_sources_list(
            async_session_maker,
            count=COUNT_IN_GROUP_2,
            source_type=SourceType.telegram,
            category_id=categories[1].id
        )
    sources_3 = await create_sources_list(
        async_session_maker,
        count=count_in_groups_1_3,
        source_type=SourceType.facebook,
        category_id=categories[0].id
    )
    sources_4 = await create_sources_list(
            async_session_maker,
            count=COUNT_IN_GROUP_2,
            source_type=SourceType.facebook,
            category_id=categories[1].id
        )

    expected_total = (count_in_groups_1_3 + COUNT_IN_GROUP_2) * 2
    base_url = "/sources/"
    if category_index is not None:
        base_url = f"{base_url}?category_id={categories[category_index].id}"
        if category_index == 0:
            expected_total = count_in_groups_1_3 * 2
        else:
            expected_total = COUNT_IN_GROUP_2 * 2

    resp_stat = ResStat()
    sources_results = get_multipage_results(
        async_client=async_client,
        base_url=base_url,
        resp_stat=resp_stat,
        limit=limit
    )
    unique_titles = {source["title"] async for source in sources_results}
    
    assert len(unique_titles) == expected_total
    if limit:
        expected_pages = ceil(expected_total / limit)
        assert resp_stat.total_pages == expected_pages, "Check number of pages"


