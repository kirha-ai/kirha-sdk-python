import json
from typing import Any

import httpx
import pytest
import respx

from kirha import (
    Account,
    ApiError,
    AsyncKirha,
    AuthenticationError,
    ConfigurationError,
    Kirha,
    KirhaError,
    NetworkError,
    PlanExpiredError,
    Planning,
    PlanStep,
    RateLimitError,
    Tool,
    ToolDetails,
    Usage,
)

API = "https://api.kirha.com"
ACCOUNT = {"balance": 396871, "balance_timestamp": "2026-10-12T14:28:23.228Z"}
STEP = {
    "id": "step_1",
    "status": "done",
    "tool_name": "defillama_searchYieldPools",
    "parameters": {"chain": "Ethereum"},
    "reasoning": "Top stablecoin pools",
}
RAW_DATA = [
    {
        "step_id": "step_1",
        "tool_name": "defillama_searchYieldPools",
        "parameters": {"chain": "Ethereum"},
        "output": {"pools": []},
    }
]
SEARCH = {
    "id": "search_1",
    "summary": "Curve leads",
    "raw_data": RAW_DATA,
    "planning": {"status": "success", "steps": [STEP]},
    "usage": {"estimated": 5, "consumed": 5},
    "account": ACCOUNT,
}
PLAN = {
    "id": "search_1",
    "status": "pending_confirmation",
    "steps": [{**STEP, "status": "pending"}],
    "usage": {"estimated": 5, "consumed": 0},
    "account": ACCOUNT,
}
TOOL = {
    "id": "tool_1",
    "name": "coingecko_searchCoin",
    "description": "Search coins",
    "provider": "coingecko",
    "credits_per_call": 2,
    "input_schema": {"type": "object"},
}
RELATED_TOOL = {
    "id": "tool_2",
    "name": "coingecko_getCoinPrice",
    "description": "Get a coin price",
    "provider": "coingecko",
    "credits_per_call": 1,
    "related": True,
    "related_to": ["coingecko_searchCoin"],
}
TOOL_RESULT = {
    "tool_name": "coingecko_searchCoin",
    "output": {"coins": []},
    "is_error": False,
    "usage": {"estimated": 1, "consumed": 1},
}
EXPIRED = {"type": "CONVERSATION_TURN_TIMEOUT", "reason": "Plan expired."}


def sent(route: respx.Route) -> Any:
    return json.loads(route.calls.last.request.content)


def queried(route: respx.Route) -> dict[str, str]:
    return dict(route.calls.last.request.url.params)


def test_search(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{API}/search/v1").respond(json=SEARCH)

    result = Kirha(api_key="test-key").search("stablecoin yields", focus="crypto")

    assert sent(route) == {"query": "stablecoin yields", "focus": "crypto"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer test-key"
    assert result.id == "search_1"
    assert result.summary == "Curve leads"
    assert result.data == RAW_DATA
    assert result.planning == Planning(
        status="success",
        steps=[
            PlanStep(
                id="step_1",
                status="done",
                tool_name="defillama_searchYieldPools",
                parameters={"chain": "Ethereum"},
                reasoning="Top stablecoin pools",
            )
        ],
    )
    assert result.usage == Usage(estimated=5, consumed=5)
    assert result.account == Account(
        balance=396871, balance_timestamp="2026-10-12T14:28:23.228Z"
    )


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"summarization": True}, {"summarization": {"enable": True}}),
        ({"summarization": {}}, {"summarization": {"enable": True}}),
        (
            {"summarization": {"instruction": "Be brief"}},
            {"summarization": {"enable": True, "instruction": "Be brief"}},
        ),
        ({"summarization": False}, {}),
        (
            {"include_data": False, "include_planning": True},
            {"include_raw_data": False, "include_planning": True},
        ),
        ({"planning_runtime": "fast"}, {"planning_runtime": "fast"}),
    ],
)
def test_search_options(
    respx_mock: respx.MockRouter, options: dict[str, Any], expected: dict[str, Any]
) -> None:
    route = respx_mock.post(f"{API}/search/v1").respond(json=SEARCH)

    Kirha(api_key="test-key").search("query", **options)

    assert sent(route) == {"query": "query", **expected}


def test_client_defaults_apply_until_overridden(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{API}/search/v1").respond(json=SEARCH)
    kirha = Kirha(
        api_key="test-key", focus="crypto", summarization={"instruction": "Be brief"}
    )

    kirha.search("query")
    assert sent(route) == {
        "query": "query",
        "focus": "crypto",
        "summarization": {"enable": True, "instruction": "Be brief"},
    }

    kirha.search("query", focus="", summarization=False)
    assert sent(route) == {"query": "query"}


def test_plan_and_execute(respx_mock: respx.MockRouter) -> None:
    plan_route = respx_mock.post(f"{API}/search/v1/plan").respond(json=PLAN)
    run_route = respx_mock.post(f"{API}/search/v1/plan/run").respond(json=SEARCH)
    kirha = Kirha(api_key="test-key", focus="crypto")

    plan = kirha.plan("query", summarization=True, planning_runtime="fast")

    assert sent(plan_route) == {
        "query": "query",
        "focus": "crypto",
        "planning_runtime": "fast",
    }
    assert (plan.id, plan.query, plan.focus, plan.status) == (
        "search_1",
        "query",
        "crypto",
        "pending_confirmation",
    )
    assert [step.status for step in plan.steps] == ["pending"]
    assert plan.usage == Usage(estimated=5, consumed=0)

    result = plan.execute(include_planning=True)
    assert sent(run_route) == {
        "id": "search_1",
        "summarization": {"enable": True},
        "include_planning": True,
    }
    assert result.summary == "Curve leads"

    plan.execute(summarization=False, include_data=False)
    assert sent(run_route) == {"id": "search_1", "include_raw_data": False}


def test_expired_plan(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{API}/search/v1/plan/run").respond(400, json=EXPIRED)

    with pytest.raises(PlanExpiredError) as caught:
        Kirha(api_key="test-key").execute_plan("search_1")

    assert caught.value.plan_id == "search_1"
    assert isinstance(caught.value.__cause__, ApiError)


def test_tools(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{API}/tools/v1").respond(
        json={"tools": [TOOL], "total": 1, "limit": 1, "skip": 0}
    )

    tools = Kirha(api_key="test-key").tools(focus="crypto")

    assert queried(route) == {"vertical_id": "crypto"}
    assert not hasattr(tools[0], "related_tools")
    assert tools == [
        Tool(
            id="tool_1",
            name="coingecko_searchCoin",
            description="Search coins",
            provider="coingecko",
            credits_per_call=2,
            input_schema={"type": "object"},
        )
    ]


def test_tools_filters(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{API}/tools/v1").respond(
        json={"tools": [TOOL], "total": 416, "limit": 20, "skip": 40}
    )
    kirha = Kirha(api_key="test-key")

    kirha.tools(focus="crypto", provider="coingecko", page=3, limit=20)
    assert queried(route) == {
        "vertical_id": "crypto",
        "provider": "coingecko",
        "page": "3",
        "limit": "20",
    }

    kirha.tools(focus="")
    assert queried(route) == {}


def test_tools_page(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{API}/tools/v1").respond(
        json={"tools": [TOOL], "total": 416, "limit": 20, "skip": 40}
    )

    page = Kirha(api_key="test-key").tools_page(focus="crypto", page=3)

    assert (page.total, page.limit, page.skip) == (416, 20, 40)
    assert [tool.name for tool in page.tools] == ["coingecko_searchCoin"]


def test_match(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{API}/tools/v1/match").respond(
        json={"tools": [TOOL, RELATED_TOOL], "total": 2, "limit": 10, "skip": 0}
    )

    page = Kirha(api_key="test-key").match("price of avax", focus="crypto", limit=10)

    assert queried(route) == {
        "q": "price of avax",
        "vertical_id": "crypto",
        "limit": "10",
    }
    assert (page.total, page.limit, page.skip) == (2, 10, 0)
    assert (page.tools[0].related, page.tools[0].related_to) == (False, [])
    assert (
        page.tools[1].name,
        page.tools[1].related,
        page.tools[1].related_to,
    ) == ("coingecko_getCoinPrice", True, ["coingecko_searchCoin"])


def test_match_without_ranking(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{API}/tools/v1/match").respond(
        json={"tools": [], "total": 0, "limit": 10, "skip": 0}
    )

    page = Kirha(api_key="test-key").match("price of avax")

    assert (page.tools, page.total) == ([], 0)
    assert queried(route) == {"q": "price of avax"}


def test_get(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{API}/tools/v1/coingecko_searchCoin").respond(
        json={**TOOL, "related_tools": ["coingecko_getCoinPrice"]}
    )

    tool = Kirha(api_key="test-key").get("coingecko_searchCoin")

    assert isinstance(tool, ToolDetails)

    assert (tool.name, tool.provider, tool.credits_per_call) == (
        "coingecko_searchCoin",
        "coingecko",
        2,
    )
    assert tool.related_tools == ["coingecko_getCoinPrice"]


def test_get_unknown(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{API}/tools/v1/nope").respond(
        404, json={"type": "NOT_FOUND", "reason": "Tool not found."}
    )

    with pytest.raises(ApiError) as caught:
        Kirha(api_key="test-key").get("nope")

    assert (caught.value.status_code, caught.value.code) == (404, "NOT_FOUND")


def test_execute_tool(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{API}/tools/v1/execute").respond(json=TOOL_RESULT)
    kirha = Kirha(api_key="test-key")

    result = kirha.execute_tool("coingecko_searchCoin", {"query": "avax"})

    assert sent(route) == {
        "tool_name": "coingecko_searchCoin",
        "input": {"query": "avax"},
    }
    assert (result.output, result.is_error, result.usage.consumed) == (
        {"coins": []},
        False,
        1,
    )

    kirha.execute_tool("coingecko_searchCoin")
    assert sent(route) == {"tool_name": "coingecko_searchCoin", "input": {}}


@pytest.mark.parametrize(
    ("response", "error_type", "code", "message"),
    [
        (
            httpx.Response(
                401, json={"type": "NOT_AUTHORIZED", "reason": "Not authorized."}
            ),
            AuthenticationError,
            "NOT_AUTHORIZED",
            "Not authorized.",
        ),
        (
            httpx.Response(
                429,
                json={"error": {"code": "rate_limit", "message": "Too many requests"}},
                headers={"Retry-After": "60"},
            ),
            RateLimitError,
            "rate_limit",
            "Too many requests",
        ),
        (
            httpx.Response(
                400, json={"error": {"code": "bad_request", "message": "Bad query"}}
            ),
            ApiError,
            "bad_request",
            "Bad query",
        ),
        (
            httpx.Response(502, text="<html>Bad Gateway</html>"),
            ApiError,
            "unknown_error",
            "HTTP 502: Bad Gateway",
        ),
        (
            httpx.Response(200, text="<html>OK</html>"),
            ApiError,
            "invalid_response",
            "Unexpected response from the Kirha API",
        ),
        (
            httpx.Response(200, json={"id": "search_1"}),
            ApiError,
            "invalid_response",
            "Unexpected response from the Kirha API",
        ),
    ],
)
def test_errors(
    respx_mock: respx.MockRouter,
    response: httpx.Response,
    error_type: type[ApiError],
    code: str,
    message: str,
) -> None:
    respx_mock.post(f"{API}/search/v1").mock(return_value=response)

    with pytest.raises(ApiError) as caught:
        Kirha(api_key="test-key").search("query")

    assert type(caught.value) is error_type
    assert (caught.value.status_code, caught.value.code, str(caught.value)) == (
        response.status_code,
        code,
        message,
    )


def test_rate_limit_retry_after(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{API}/search/v1").respond(429, headers={"Retry-After": "60"})

    with pytest.raises(RateLimitError) as caught:
        Kirha(api_key="test-key").search("query")

    assert caught.value.retry_after == 60


def test_network_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{API}/search/v1").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(NetworkError) as caught:
        Kirha(api_key="test-key").search("query")

    assert isinstance(caught.value, KirhaError)
    assert isinstance(caught.value.__cause__, httpx.ConnectError)


def test_api_key_from_environment(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = respx_mock.post(f"{API}/search/v1").respond(json=SEARCH)
    monkeypatch.setenv("KIRHA_API_KEY", "env-key")

    Kirha().search("query")

    assert route.calls.last.request.headers["Authorization"] == "Bearer env-key"


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KIRHA_API_KEY", raising=False)

    with pytest.raises(ConfigurationError):
        Kirha()


@pytest.mark.anyio
async def test_async_client(respx_mock: respx.MockRouter) -> None:
    search_route = respx_mock.post(f"{API}/search/v1").respond(json=SEARCH)
    respx_mock.post(f"{API}/search/v1/plan").respond(json=PLAN)
    run_route = respx_mock.post(f"{API}/search/v1/plan/run").respond(json=SEARCH)
    respx_mock.get(f"{API}/tools/v1").respond(
        json={"tools": [TOOL], "total": 416, "limit": 20, "skip": 40}
    )
    match_route = respx_mock.get(f"{API}/tools/v1/match").respond(
        json={"tools": [TOOL, RELATED_TOOL], "total": 2, "limit": 10, "skip": 0}
    )
    respx_mock.get(f"{API}/tools/v1/coingecko_searchCoin").respond(
        json={**TOOL, "related_tools": ["coingecko_getCoinPrice"]}
    )
    respx_mock.post(f"{API}/tools/v1/execute").respond(json=TOOL_RESULT)

    async with AsyncKirha(api_key="test-key", summarization=True) as kirha:
        result = await kirha.search("query", focus="crypto")
        plan = await kirha.plan("query")
        executed = await plan.execute()
        tools = await kirha.tools(focus="crypto")
        page = await kirha.tools_page(focus="crypto", page=3)
        matched = await kirha.match("price of avax", focus="crypto")
        tool = await kirha.get("coingecko_searchCoin")
        tool_result = await kirha.execute_tool("coingecko_searchCoin")

    assert sent(search_route) == {
        "query": "query",
        "focus": "crypto",
        "summarization": {"enable": True},
    }
    assert result.summary == "Curve leads"
    assert plan.status == "pending_confirmation"
    assert sent(run_route) == {"id": "search_1", "summarization": {"enable": True}}
    assert executed.id == "search_1"
    assert [t.name for t in tools] == ["coingecko_searchCoin"]
    assert (page.total, page.skip) == (416, 40)
    assert queried(match_route) == {"q": "price of avax", "vertical_id": "crypto"}
    assert matched.total == 2
    assert (matched.tools[1].related, matched.tools[1].related_to) == (
        True,
        ["coingecko_searchCoin"],
    )
    assert tool.related_tools == ["coingecko_getCoinPrice"]
    assert tool_result.tool_name == "coingecko_searchCoin"


@pytest.mark.anyio
async def test_async_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{API}/search/v1/plan/run").respond(400, json=EXPIRED)
    respx_mock.post(f"{API}/search/v1").mock(side_effect=httpx.ReadTimeout("slow"))

    async with AsyncKirha(api_key="test-key") as kirha:
        with pytest.raises(PlanExpiredError):
            await kirha.execute_plan("search_1")
        with pytest.raises(NetworkError):
            await kirha.search("query")
