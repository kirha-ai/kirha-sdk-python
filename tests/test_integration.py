import os

import pytest

from kirha import AsyncKirha, Kirha

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("KIRHA_API_KEY"), reason="KIRHA_API_KEY is not set"
    ),
]


def test_search() -> None:
    with Kirha(focus="crypto") as kirha:
        result = kirha.search(
            "What is the current Bitcoin price in USD?",
            summarization=True,
            include_planning=True,
        )

    assert result.id.startswith("search_")
    assert result.summary
    assert result.data
    assert result.planning is not None
    assert result.usage.consumed >= 0


def test_plan_and_execute() -> None:
    with Kirha() as kirha:
        plan = kirha.plan("What is the current Bitcoin price in USD?", focus="crypto")
        assert plan.status == "pending_confirmation"
        assert plan.steps

        result = plan.execute(include_planning=True)

    assert result.id == plan.id
    assert result.data
    assert result.planning is not None


def test_tools() -> None:
    with Kirha() as kirha:
        tools = kirha.tools(focus="crypto")
        result = kirha.execute_tool(
            "coingecko_searchCoin", {"query": "avax", "limit": 1}
        )

    assert any(tool.name == "coingecko_searchCoin" for tool in tools)
    assert not result.is_error
    assert result.output


@pytest.mark.anyio
async def test_async_search() -> None:
    async with AsyncKirha() as kirha:
        result = await kirha.search(
            "What is the current Ethereum price in USD?",
            focus="crypto",
            planning_runtime="fast",
        )

    assert result.data
