from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

import httpx

if TYPE_CHECKING:
    from typing_extensions import Self

from ._errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    PlanExpiredError,
    RateLimitError,
)
from ._models import (
    Account,
    PlanningRuntime,
    PlanStep,
    SearchResult,
    Summarization,
    Tool,
    ToolExecutionResult,
    Usage,
    parse_plan,
    parse_search_result,
    parse_tool_execution_result,
    parse_tools,
)

BASE_URL = "https://api.kirha.com"
DEFAULT_TIMEOUT = 120.0
PLAN_EXPIRED_CODE = "CONVERSATION_TURN_TIMEOUT"

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class _PlanFields:
    id: str
    query: str
    focus: str | None
    status: str
    steps: list[PlanStep]
    usage: Usage
    account: Account
    reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class Plan(_PlanFields):
    _client: Kirha = field(repr=False, compare=False)
    _summarization: bool | Summarization | None = field(
        default=None, repr=False, compare=False
    )

    def execute(
        self,
        *,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
    ) -> SearchResult:
        if summarization is None:
            summarization = self._summarization
        return self._client.execute_plan(
            self.id,
            summarization=summarization,
            include_data=include_data,
            include_planning=include_planning,
        )


@dataclass(frozen=True, kw_only=True)
class AsyncPlan(_PlanFields):
    _client: AsyncKirha = field(repr=False, compare=False)
    _summarization: bool | Summarization | None = field(
        default=None, repr=False, compare=False
    )

    async def execute(
        self,
        *,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
    ) -> SearchResult:
        if summarization is None:
            summarization = self._summarization
        return await self._client.execute_plan(
            self.id,
            summarization=summarization,
            include_data=include_data,
            include_planning=include_planning,
        )


class _BaseClient:
    def __init__(
        self,
        api_key: str | None,
        focus: str | None,
        summarization: bool | Summarization | None,
    ) -> None:
        api_key = api_key or os.environ.get("KIRHA_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "api_key is required: pass it or set KIRHA_API_KEY"
            )
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._focus = focus
        self._summarization = summarization

    def _search_body(
        self,
        query: str,
        focus: str | None,
        summarization: bool | Summarization | None,
        include_data: bool | None,
        include_planning: bool | None,
        planning_runtime: PlanningRuntime | None,
    ) -> dict[str, Any]:
        return _compact(
            query=query,
            focus=self._resolve_focus(focus),
            summarization=self._summarization_body(summarization),
            include_raw_data=include_data,
            include_planning=include_planning,
            planning_runtime=planning_runtime,
        )

    def _plan_body(
        self, query: str, focus: str | None, planning_runtime: PlanningRuntime | None
    ) -> dict[str, Any]:
        return _compact(
            query=query,
            focus=self._resolve_focus(focus),
            planning_runtime=planning_runtime,
        )

    def _run_body(
        self,
        plan_id: str,
        summarization: bool | Summarization | None,
        include_data: bool | None,
        include_planning: bool | None,
    ) -> dict[str, Any]:
        return _compact(
            id=plan_id,
            summarization=self._summarization_body(summarization),
            include_raw_data=include_data,
            include_planning=include_planning,
        )

    def _resolve_focus(self, focus: str | None) -> str | None:
        return (self._focus if focus is None else focus) or None

    def _summarization_body(
        self, summarization: bool | Summarization | None
    ) -> dict[str, Any] | None:
        value = self._summarization if summarization is None else summarization
        if isinstance(value, dict):
            return _compact(enable=True, instruction=value.get("instruction"))
        return {"enable": True} if value else None


class Kirha(_BaseClient):
    def __init__(
        self,
        api_key: str | None = None,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(api_key, focus, summarization)
        self._http = httpx.Client(
            base_url=BASE_URL, headers=self._headers, timeout=timeout
        )

    def search(
        self,
        query: str,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
        planning_runtime: PlanningRuntime | None = None,
    ) -> SearchResult:
        body = self._search_body(
            query,
            focus,
            summarization,
            include_data,
            include_planning,
            planning_runtime,
        )
        return self._request("POST", "/search/v1", parse_search_result, json=body)

    def plan(
        self,
        query: str,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        planning_runtime: PlanningRuntime | None = None,
    ) -> Plan:
        body = self._plan_body(query, focus, planning_runtime)
        fields = self._request("POST", "/search/v1/plan", parse_plan, json=body)
        return Plan(
            **fields,
            query=query,
            focus=body.get("focus"),
            _client=self,
            _summarization=summarization,
        )

    def execute_plan(
        self,
        plan_id: str,
        *,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
    ) -> SearchResult:
        body = self._run_body(plan_id, summarization, include_data, include_planning)
        try:
            return self._request(
                "POST", "/search/v1/plan/run", parse_search_result, json=body
            )
        except ApiError as error:
            if error.code == PLAN_EXPIRED_CODE:
                raise PlanExpiredError(plan_id) from error
            raise

    def tools(self, *, focus: str) -> list[Tool]:
        return self._request(
            "GET", "/tools/v1", parse_tools, params={"vertical_id": focus}
        )

    def execute_tool(
        self, tool_name: str, input: dict[str, Any] | None = None
    ) -> ToolExecutionResult:
        body = {"tool_name": tool_name, "input": input or {}}
        return self._request(
            "POST", "/tools/v1/execute", parse_tool_execution_result, json=body
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self, method: str, path: str, parse: Callable[[Any], T], **kwargs: Any
    ) -> T:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.TransportError as error:
            raise NetworkError(
                f"Request to {BASE_URL}{path} failed: {error!r}"
            ) from error
        return _handle(response, parse)


class AsyncKirha(_BaseClient):
    def __init__(
        self,
        api_key: str | None = None,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(api_key, focus, summarization)
        self._http = httpx.AsyncClient(
            base_url=BASE_URL, headers=self._headers, timeout=timeout
        )

    async def search(
        self,
        query: str,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
        planning_runtime: PlanningRuntime | None = None,
    ) -> SearchResult:
        body = self._search_body(
            query,
            focus,
            summarization,
            include_data,
            include_planning,
            planning_runtime,
        )
        return await self._request("POST", "/search/v1", parse_search_result, json=body)

    async def plan(
        self,
        query: str,
        *,
        focus: str | None = None,
        summarization: bool | Summarization | None = None,
        planning_runtime: PlanningRuntime | None = None,
    ) -> AsyncPlan:
        body = self._plan_body(query, focus, planning_runtime)
        fields = await self._request("POST", "/search/v1/plan", parse_plan, json=body)
        return AsyncPlan(
            **fields,
            query=query,
            focus=body.get("focus"),
            _client=self,
            _summarization=summarization,
        )

    async def execute_plan(
        self,
        plan_id: str,
        *,
        summarization: bool | Summarization | None = None,
        include_data: bool | None = None,
        include_planning: bool | None = None,
    ) -> SearchResult:
        body = self._run_body(plan_id, summarization, include_data, include_planning)
        try:
            return await self._request(
                "POST", "/search/v1/plan/run", parse_search_result, json=body
            )
        except ApiError as error:
            if error.code == PLAN_EXPIRED_CODE:
                raise PlanExpiredError(plan_id) from error
            raise

    async def tools(self, *, focus: str) -> list[Tool]:
        return await self._request(
            "GET", "/tools/v1", parse_tools, params={"vertical_id": focus}
        )

    async def execute_tool(
        self, tool_name: str, input: dict[str, Any] | None = None
    ) -> ToolExecutionResult:
        body = {"tool_name": tool_name, "input": input or {}}
        return await self._request(
            "POST", "/tools/v1/execute", parse_tool_execution_result, json=body
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def _request(
        self, method: str, path: str, parse: Callable[[Any], T], **kwargs: Any
    ) -> T:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.TransportError as error:
            raise NetworkError(
                f"Request to {BASE_URL}{path} failed: {error!r}"
            ) from error
        return _handle(response, parse)


def _compact(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


def _handle(response: httpx.Response, parse: Callable[[Any], T]) -> T:
    if not response.is_success:
        raise _api_error(response)
    try:
        return parse(response.json())
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise ApiError(
            "Unexpected response from the Kirha API",
            response.status_code,
            "invalid_response",
            response.text,
        ) from error


def _api_error(response: httpx.Response) -> ApiError:
    status = response.status_code
    try:
        body = response.json()
    except ValueError:
        body = None

    nested = body.get("error") if isinstance(body, dict) else None
    if isinstance(nested, dict) and "message" in nested:
        message = nested["message"]
        code = nested.get("code", "unknown_error")
        details = nested.get("details")
    elif isinstance(body, dict) and "reason" in body:
        message, code, details = body["reason"], body.get("type", "unknown_error"), None
    else:
        message = f"HTTP {status}: {response.reason_phrase}"
        code, details = "unknown_error", body

    if status == 401:
        return AuthenticationError(message, status, code, details)
    if status == 429:
        retry_after = response.headers.get("Retry-After", "")
        return RateLimitError(
            message,
            status,
            code,
            details,
            int(retry_after) if retry_after.isdigit() else None,
        )
    return ApiError(message, status, code, details)
